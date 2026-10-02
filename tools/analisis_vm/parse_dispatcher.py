#!/usr/bin/env python3
"""Parser del dispatcher v14.8 (limpio): camina el if-chain binario sobre `i`
manteniendo el intervalo [lo,hi). Cuando el intervalo es unitario, el bloque
entero ES el handler de ese opcode. Normaliza numerales mangled.

Salida: scripts/v148_opcodes_full.json (opcode -> texto del handler)
"""
import json
import re
import sys

SRC = 'samples/cokeboys_v148.lua'
OUT = '/home/z/my-project/scripts/v148_opcodes_full.json'

NUM_RE = re.compile(r'0[xX][0-9a-fA-F_]+|0[bB][01_]+|\d+')
IDENT_RE = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')


def parse_num(s):
    s = s.replace('_', '')
    if s[:2] in ('0x', '0X'):
        return int(s[2:], 16)
    if s[:2] in ('0b', '0B'):
        return int(s[2:], 2)
    return int(s)


def tokenize(text):
    toks = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in ' \t\r\n':
            i += 1
            continue
        if c in '\'"':
            j = i + 1
            while j < n and text[j] != c:
                if text[j] == '\\':
                    j += 2
                else:
                    j += 1
            toks.append(('str', text[i:j + 1]))
            i = j + 1
            continue
        if text.startswith('--', i):
            j = text.find('\n', i)
            i = n if j < 0 else j + 1
            continue
        if c.isdigit() or text[i:i + 2] in ('0x', '0X', '0b', '0B'):
            m = NUM_RE.match(text, i)
            if m:
                toks.append(('num', parse_num(m.group(0))))
                i = m.end()
                continue
        m = IDENT_RE.match(text, i)
        if m:
            toks.append(('id', m.group(0)))
            i = m.end()
            continue
        for op in ('==', '~=', '<=', '>=', '...', '..'):
            if text.startswith(op, i):
                toks.append(('op', op))
                i += len(op)
                break
        else:
            toks.append(('op', c))
            i += 1
    return toks


def toks_text(toks):
    return ' '.join(str(v) for _, v in toks if v is not None)


class P:
    def __init__(self, toks):
        self.t = toks
        self.i = 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else ('eof', None)

    def next(self):
        tok = self.peek()
        self.i += 1
        return tok

    def at_kw(self, kw):
        t = self.peek()
        return t[0] == 'id' and t[1] == kw


COND_END = {'then'}


def read_cond(p):
    """tokens de la condicion hasta 'then' (sin consumirlo)"""
    toks = []
    while not p.at_kw('then'):
        t = p.peek()
        if t[0] == 'eof':
            break
        toks.append(p.next())
    return toks


def norm_cond(toks):
    """quita not/parens externos; devuelve ('cmp', op, val) o None"""
    t = list(toks)
    neg = False
    while t and t[0] in (('id', 'not'), ('op', '(')):
        if t[0] == ('id', 'not'):
            neg = not neg
            t = t[1:]
        elif t[0] == ('op', '(') and t[-1] == ('op', ')'):
            t = t[1:-1]
        else:
            break
    if len(t) == 3 and t[0] == ('id', 'i') and t[1][0] == 'op' and t[2][0] == 'num':
        op, val = t[1][1], t[2][1]
        if neg:
            op = {'<': '>=', '<=': '>', '>': '<=', '>=': '<',
                  '==': '~=', '~=': '=='}[op]
        return op, val
    return None


def split_interval(op, v, lo, hi):
    """(then_ivs, else_ivs) - listas de (lo,hi) - segun i OP v"""
    def clip(a, b):
        return (max(lo, a), min(hi, b))

    if op == '<':
        return [clip(lo, v)], [clip(v, hi)]
    if op == '<=':
        return [clip(lo, v + 1)], [clip(v + 1, hi)]
    if op == '>':
        return [clip(v + 1, hi)], [clip(lo, v + 1)]
    if op == '>=':
        return [clip(v, hi)], [clip(lo, v)]
    if op == '==':
        if lo <= v < hi:
            els = [clip(lo, v), clip(v + 1, hi)]
            return [(v, v + 1)], [e for e in els if e[0] < e[1]]
        return [(lo, lo)], [clip(lo, hi)]
    if op == '~=':
        if lo <= v < hi:
            th = [clip(lo, v), clip(v + 1, hi)]
            th = [e for e in th if e[0] < e[1]]
            return th, [(v, v + 1)]
        return [clip(lo, hi)], [(lo, lo)]
    return None


HANDLERS = {}


def skip_balanced(p, stop_at_caller_boundary=False):
    """consume tokens balanceados hasta volver al nivel del caller
    (end/else/elseif del bloque actual). Devuelve los tokens."""
    toks = []
    depth = 0
    while True:
        t = p.peek()
        if t[0] == 'eof':
            return toks
        if t[0] == 'id' and t[1] in ('if', 'while', 'for', 'function', 'do'):
            depth += 1
        elif t[0] == 'id' and t[1] in ('end', 'until'):
            if depth == 0:
                return toks
            depth -= 1
        elif depth == 0 and t[0] == 'id' and t[1] in ('else', 'elseif'):
            return toks
        elif depth == 0 and t[1] == ';':
            toks.append(p.next())
            return toks
        toks.append(p.next())


TRACE = [0]


def branch(p, ivs):
    """parsea una rama: intervalo vacio = texto muerto (se consume sin grabar)."""
    if not ivs:
        skip_balanced(p)
        return
    parse_block(p, ivs)


def parse_block(p, ivs):
    """bloque con intervalos ivs (lista de (lo,hi)). Unitario -> handler."""
    if not ivs:
        return
    if len(ivs) == 1 and ivs[0][1] - ivs[0][0] == 1 and ivs[0][0] >= 0:
        lo = ivs[0][0]
        toks = skip_balanced(p)
        if lo not in HANDLERS:
            HANDLERS[lo] = toks_text(toks)
        return
    lo = min(e[0] for e in ivs)
    hi = max(e[1] for e in ivs)
    while True:
        t = p.peek()
        if t[0] == 'eof':
            return
        if t[0] == 'id' and t[1] in ('end', 'else', 'elseif'):
            return
        if t[0] == 'id' and t[1] == 'if':
            p.next()
            cond = read_cond(p)
            if not p.at_kw('then'):
                skip_balanced(p)
                continue
            p.next()  # then
            nc = norm_cond(cond)
            if nc is None:
                if TRACE[0] < 70:
                    TRACE[0] += 1
                    print('  [t%d] no-i-cond %s..%s: %s' % (
                        TRACE[0], lo, hi, toks_text(cond)[:60]))
                skip_balanced(p)
                continue
            th, el = split_interval(nc[0], nc[1], lo, hi)
            if TRACE[0] < 70:
                TRACE[0] += 1
                print('  [t%d] %s..%s %s -> then %s else %s' % (
                    TRACE[0], lo, hi, toks_text(cond)[:40],
                    [e for e in th if e[0] < e[1]], [e for e in el if e[0] < e[1]]))
            branch(p, [e for e in th if e[0] < e[1]])
            t2 = p.peek()
            if t2 == ('id', 'else'):
                p.next()
                branch(p, [e for e in el if e[0] < e[1]])
                if p.at_kw('end'):
                    p.next()
            elif t2 == ('id', 'elseif'):
                parse_elseif(p, [e for e in el if e[0] < e[1]])
            elif t2 == ('id', 'end'):
                p.next()
            continue
        # statement comun
        skip_balanced(p)


def parse_elseif(p, rest):
    while True:
        t = p.peek()
        if t == ('id', 'end'):
            p.next()
            return
        if t != ('id', 'elseif'):
            return
        p.next()
        cond = read_cond(p)
        p.next()  # then
        nc = norm_cond(cond)
        if nc is None:
            skip_balanced(p)
            # seguir buscando elseif/end
            continue
        lo = min(e[0] for e in rest)
        hi = max(e[1] for e in rest)
        th, el = split_interval(nc[0], nc[1], lo, hi)
        branch(p, [e for e in th if e[0] < e[1]])
        t2 = p.peek()
        if t2 == ('id', 'else'):
            p.next()
            branch(p, [e for e in el if e[0] < e[1]])
            if p.at_kw('end'):
                p.next()
            return
        rest = [e for e in el if e[0] < e[1]]
        if not rest:
            while not p.at_kw('end') and p.peek()[0] != 'eof':
                skip_balanced(p)
            if p.at_kw('end'):
                p.next()
            return


def main():
    src = open(SRC, 'rb').read().decode('latin-1')
    m = re.search(r'while true do local (\w+)=\((\w+)\[(\w+)\]\);', src)
    if not m:
        sys.exit('no dispatcher')
    chain = src[m.start():m.start() + 900000]
    toks = tokenize(chain)
    print('[*] tokens: %d' % len(toks))
    p = P(toks)
    # cabecera: while true do local i = ( F [ x ] ) ;
    for _ in range(10):
        p.next()
    sys.setrecursionlimit(20000)
    try:
        parse_block(p, [(0, 4000)])
    except RecursionError:
        print('[!] recursion limit')
    # consume el resto: la cola del loop (x+=1 etc) - no importa
    print('[*] opcodes extraidos: %d' % len(HANDLERS))
    ks = sorted(HANDLERS)
    print('[*] rango: %d..%d' % (ks[0], ks[-1]))
    need = [58, 16, 430, 539, 314, 281, 425, 459, 472, 432, 156, 56, 30, 20, 445, 169, 9, 175, 233, 96, 371, 68, 234, 489, 35, 64, 266, 233]
    print('[*] presentes del loop: %s' % [o for o in need if o in HANDLERS])
    with open(OUT, 'w') as f:
        json.dump(HANDLERS, f, indent=1)
    print('[+] escrito', OUT)
    for o in [430, 539, 16, 58, 314, 281, 425, 459, 472, 432, 156, 56, 30, 20, 445]:
        if o in HANDLERS:
            print('op %-4d: %s' % (o, HANDLERS[o][:150]))


if __name__ == '__main__':
    main()
