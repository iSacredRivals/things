"""Loop-guard injection for Luraph v14.8 scripts.

Luraph v14.8 protects its payload with a stage key derived from live engine
values (Path2D curve answers on this sample family). When the offline
environment's answers are not bit-exact, the VM's decode loop runs forever
without touching the environment again - the tracer's budget (which fires on
environment access) never triggers and the run dies at the hard timeout with
nothing written.

This module injects a counter at the head of every while/repeat loop of the
script (AST-located, so strings and comments are never touched). The counter
is TABLE OPERATIONS ONLY (no call, no new locals: a call would add a stack
frame every iteration, and Luraph mixes stack depth into its probes); every
STEP iterations one __LC.f(n) call checks the guard:

* an iteration cap per loop (VM dispatch loops get a huge one - they
  legitimately run tens of millions of instructions);
* a time bound (--v14-spin-seconds): pure-compute phases never emit, so the
  emit-based budget cannot see them; the guard is what bounds them;
* a trace throttle: when the tracer's own block fills (envlog's emit silences
  itself and pushes a continuation block), the guard's unconditional
  __VMBEAT keeps that silence alive only while the loop is actually running,
  and __LC.r(n) - injected after the loop's `end` - turns tracing back on.
  A loop's emissions stay in the result unless they were actually drowning
  the tracer (the block limit decides, not the loop's shape).

A loop that crosses a bound errors out with `@@SPINLOOP <n>`, which envlog
reports like any script error - the trace gathered so far is dumped normally,
and the plugin turns the marker into an actionable note.
"""
import re

import luauast

FETCH = re.compile(r'\s*local\s+(\w+)\s*=\s*\(?\s*(\w+)\s*\[\s*(\w+)\s*\]\s*\)?\s*;')

STEP = 4096            # iterations between guard checks (table ops between them)


def _loops_of(source):
    ast = luauast.parse(source)
    found = []

    def walk(node):
        if isinstance(node, dict):
            if node.get('type') in ('AstStatWhile', 'AstStatRepeat'):
                found.append(node)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(ast)
    return ast, found


def _offsets(source):
    lines = source.split('\n')
    off = [0]
    for l in lines:
        off.append(off[-1] + len(l) + 1)
    return off


def _to_off(off, loc):
    # luau-ast lines are 0-based (columns too), like vmmap's `lines[l1]`
    m = re.match(r'(\d+),(\d+)', loc)
    if not m:
        return None
    return off[int(m.group(1))] + int(m.group(2))


def _end_off(off, loc):
    m = re.match(r'\d+,\d+ - (\d+),(\d+)', loc)
    if not m:
        return None
    return off[int(m.group(1))] + int(m.group(2))


def _first_stmt_off(ast, off):
    """Offset of the first top-level statement: the prelude goes right before
    it, i.e. after every leading comment. A block comment at the top of the
    file (`--[[ Luarmor bootstrapper ... ]]`, obf_4) used to swallow the whole
    prelude - `__LC` then resolved as an unknown GLOBAL (a logging proxy), and
    every guard call was traced as a statement, drowning the run."""
    body = (ast or {}).get('body') or []
    for node in body:
        o = _to_off(off, node.get('location') or '')
        if o is not None:
            return o
    return 0


def inject(source, vm_cap=250_000_000, plain_cap=50_000_000, spin_seconds=0):
    """(guarded_source, n_loops, n_vm) - source unchanged (0, 0) when it does
    not parse (the run then relies on the plain timeout only)."""
    try:
        ast, loops = _loops_of(source)
    except SyntaxError:
        return source, 0, 0
    if not loops:
        return source, 0, 0
    off = _offsets(source)
    ins = []      # (offset, code) - loop heads, in source order
    tails = []    # (loop id, offset of the loop's end) - re-arm injections
    for n, node in enumerate(loops):
        if node['type'] == 'AstStatWhile':
            j = _end_off(off, node['condition']['location'])
            if j is None:
                continue
            while j < len(source) and source[j] in ' \t\r\n':
                j += 1
            if source.startswith('do', j):
                j += 2
            else:
                k = source.find('do', j)
                if k < 0 or k > j + 20:
                    continue
                j = k + 2
            ins.append((j, n))
        else:
            st = _to_off(off, node['location'])
            if st is None:
                continue
            k = source.rfind('repeat', max(0, st - 10), st + 10)
            st = k if k >= 0 else st
            if not source.startswith('repeat', st):
                continue
            ins.append((st + len('repeat'), n))
        end = _end_off(off, node['location'])
        if end is not None:
            tails.append((end, n))
    if not ins:
        return source, 0, 0

    # classify VM dispatch loops: opcode fetch right at the head
    vm = set()
    for j, n in ins:
        node = loops[n]
        cond = node.get('condition') or {}
        if (node['type'] == 'AstStatWhile'
                and cond.get('type') == 'AstExprConstantBool' and cond.get('value')):
            if FETCH.match(source, j):
                vm.add(n)

    head = " __LC[%d].c+=1;if __LC[%d].c>=%d then __LC.f(%d)end;"
    edits = [(j, head % (n, n, STEP, n)) for j, n in ins]
    edits += [(e, " __LC.r(%d);" % n) for e, n in tails]
    edits.sort(key=lambda t: t[0], reverse=True)
    out = source
    for j, code in edits:
        out = out[:j] + code + out[j:]

    caps = '{' + ','.join('[%d]=%d' % (n, vm_cap if n in vm else plain_cap)
                          for n in range(len(loops))) + '}'
    # LINE-PRESERVING prelude: Luraph v14.8 hashes debug.info(f, "sl") of its
    # own functions (self-integrity). A multi-line prelude shifts every line
    # after it and trips the check (observed: buffer.create(size out of range)
    # tamper response). So: strip the comments, flatten to ONE line and insert
    # at the first statement's offset WITHOUT a leading newline -> zero shift.
    prelude = (
        'local __LC = ({}); '
        'for __n = 0, %d do __LC[__n] = {c = 0, n = 0}; end '
        'local __CLK = os.clock; local __T0 = __CLK(); local __SPINSEC = %d; '
        'local function __LCprint(n, c) local v = __VMHOT; if v then v(true) end; '
        'print("@@SPINLOOP " .. n .. " iter=" .. c) '
        'error("v14 loop " .. n .. " hit its guard (iteration cap or time bound)", 0) end '
        'local __CAP = %s; '
        '__LC.f = function(i) local t = __LC[i]; t.n = t.n + t.c; t.c = 0; '
        '  if t.n > (__CAP[i] or %d) then __LCprint(i, t.n) end; '
        '  if __SPINSEC > 0 and __CLK() - __T0 > __SPINSEC then __LCprint(i, t.n) end; '
        '  local b = __VMBEAT; if b then b() end end '
        '__LC.r = function(i) local v = __VMHOT; if v then v(true) end end '
    ) % (len(loops) - 1, spin_seconds, caps, plain_cap)
    at = _first_stmt_off(ast, off)
    out = out[:at] + prelude + out[at:]
    return out, len(ins), len(vm)


SPIN_STMT = re.compile(r'\n?--@\d+[^\n]*\n?print\("@@SPINLOOP (\d+) iter=\d+"\)\n?')


def strip_spin_markers(body):
    """Remove the traced `print("@@SPINLOOP ...")` statements; return
    (body, [loop ids])."""
    ids = []

    def sub(m):
        ids.append(m.group(1))
        return '\n'

    return SPIN_STMT.sub(sub, body), ids
