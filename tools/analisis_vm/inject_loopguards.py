"""Inject iteration counters into every while/repeat loop of the v14.8 script
to find which loop spins forever in the envlog environment.

Output: samples/cokeboys_v148_guarded.lua
The guard prints @@STUCKLOOP <id> and errors after MAXIT iterations.
"""
import re
import sys

sys.path.insert(0, 'deobf')
import luauast

SRC_PATH = '/home/z/my-project/downloads_cdn/message_test_v148.txt'
OUT_PATH = 'samples/cokeboys_v148_guarded.lua'
# a loop may spin at most this many CPU-seconds without touching the
# environment before it is declared stuck (VM dispatch loops legitimately run
# millions of instructions, but they make progress through env access)
SPIN_SECONDS = float(sys.argv[1]) if len(sys.argv) > 1 else 45.0
VM_LOOP_CAP = 400_000_000   # VM dispatch loops: instruction cap
PLAIN_CAP = 5_000_000      # other loops: iteration cap

src = open(SRC_PATH, 'rb').read().decode('latin-1')
lines = src.split('\n')
line_off = [0]
for l in lines:
    line_off.append(line_off[-1] + len(l) + 1)


def to_off(loc):
    m = re.match(r'(\d+),(\d+)', loc)
    if not m:
        return None
    return line_off[int(m.group(1)) - 1] + int(m.group(2))


def loc_end(loc):
    m = re.match(r'\d+,\d+ - (\d+),(\d+)', loc)
    if not m:
        return None
    # end is exclusive-ish: col points one past the last char
    return line_off[int(m.group(1)) - 1] + int(m.group(2))


ast = luauast.parse(src)
loops = []


def walk(node):
    if isinstance(node, dict):
        t = node.get('type', '')
        if t in ('AstStatWhile', 'AstStatRepeat'):
            loops.append(node)
        for v in node.values():
            walk(v)
    elif isinstance(node, list):
        for v in node:
            walk(v)


walk(ast)
print('while/repeat loops:', len(loops))

# build insertion points (descending offset for stable injection)
ins = []
for n, node in enumerate(loops):
    if node['type'] == 'AstStatWhile':
        cond_end = loc_end(node['condition']['location'])
        if cond_end is None:
            continue
        # after the condition: whitespace, then 'do'
        j = cond_end
        while j < len(src) and src[j] in ' \t\r\n':
            j += 1
        if src.startswith('do', j):
            j += 2
        else:
            # e.g. condition end misparsed; fall back: skip to next 'do'
            k = src.find('do', j)
            if k < 0 or k > j + 20:
                continue
            j = k + 2
        ins.append((j, n))
    else:  # Repeat
        st = to_off(node['location'])
        if st is None or not src.startswith('repeat', st):
            # location start may be off; search backwards a little
            k = src.rfind('repeat', max(0, st - 10), st + 10)
            if k < 0:
                continue
            st = k
        ins.append((st + len('repeat'), n))

ins.sort(reverse=True)
print('insertion points:', len(ins))

# classify: VM dispatch loops (opcode fetch right after `while true do`)
# get the huge cap; plain loops get the small one
vm_loops = set()
FETCH = re.compile(r'\s*local\s+(\w+)\s*=\s*\(?\s*(\w+)\s*\[\s*(\w+)\s*\]\s*\)?\s*;')
for off, n in ins:
    node = loops[n]
    cond = node.get('condition') or {}
    is_true = cond.get('type') == 'AstExprConstantBool' and cond.get('value') is True
    if node['type'] == 'AstStatWhile' and is_true:
        m = FETCH.match(src, off)
        if m:
            vm_loops.add(n)
print('VM dispatch loops:', sorted(vm_loops))

caps = '{' + ','.join('[%d]=%d' % (n, VM_LOOP_CAP if n in vm_loops else PLAIN_CAP) for n in range(len(loops))) + '}'

out = src
for off, n in ins:
    out = out[:off] + ' __LC[%d]();' % n + out[off:]

# per-loop guards in a TABLE (Luau caps locals at 200): iteration caps
guard_src = (
    'local __LOOPCT = ({}); local __CAP = %s;\n'
    'local function __LCprint(n, c) print("@@SPINLOOP " .. n .. " iter=" .. c) '
    'error("spin loop " .. n, 0) end\n'
    'local __LC = ({});\n'
    'for __n = 0, %d do __LC[__n] = function() '
    'local c = (__LOOPCT[__n] or 0) + 1; __LOOPCT[__n] = c; '
    'if c > (__CAP[__n] or %d) then __LCprint(__n, c) end; '
    'return c; end; end\n'
) % (caps, len(loops) - 1, PLAIN_CAP)


# The script is `-- header\n\nreturn({...})`: inject locals BEFORE the return,
# after the header comment lines.
m = re.match(r'(--[^\n]*\n)', out)
head = m.group(1) if m else ''
body = out[len(head):]
out = head + '\n' + guard_src + body
open(OUT_PATH, 'w', encoding='latin-1', newline='\n').write(out)
print('wrote', OUT_PATH, len(out), 'bytes')

# quick syntax check with luau (it compiles the whole file when run)
import subprocess
r = subprocess.run(['deobf/bin/luau', OUT_PATH],
                   capture_output=True, timeout=60)
print('syntax check rc:', r.returncode)
err = r.stderr.decode('utf-8', 'replace')
if r.returncode != 0 and 'attempt to index' not in err:
    print(err[:800])
elif r.returncode != 0:
    print('[ok] parses; runtime error expected in bare luau:', err[:200])