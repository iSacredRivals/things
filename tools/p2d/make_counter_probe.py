#!/usr/bin/env python3
"""Sonda contador v2 - DESPLAZAMIENTO CERO de lineas:
la sonda vive en la MISMA linea 2 del script original (sin \\n nuevos), para
que los linedefined/currentline de todas las funciones del script queden
IDENTICOS a los del original (el VM de Luraph puede verificarlos).
El usuario la corre en Delta y reporta el ultimo [CNT] + tiempo de carga."""
import re
import sys

SRC = 'samples/cokeboys_v148.lua'
OUT = '/home/z/my-project/download/cokeboys_counter_probe.lua'

# prelude en UNA sola linea (sin saltos)
PRELUDE = ('local __CNT=0;local function __CSTEP() __CNT=__CNT+1; '
           'if __CNT%10000000==0 then print("[CNT] "..__CNT.." iters "..'
           'tostring(math.floor(os.clock())).."s") end end; ')
CALL = ' __CSTEP(); '


def main():
    src = open(SRC, 'rb').read().decode('latin-1')
    # cabecera (linea 1) + cuerpo (linea 2, una sola linea gigante)
    m = re.match(r'(--[^\n]*\n)', src)
    head = m.group(1) if m else ''
    body = src[len(head):]
    nl = body.count('\n')
    print('[*] lineas del cuerpo original: %d (esperado 1)' % nl)
    # localizar el dispatcher en el ORIGINAL
    d = re.search(r'while true do local (\w+)=\((\w+)\[(\w+)\]\);', body)
    if not d:
        sys.exit('[!] dispatcher no encontrado')
    fetch_end = d.end()
    print('[*] dispatcher en offset %d: %s' % (fetch_end, d.group(0)[:50]))
    # insertar el contador INLINE (sin \n)
    newbody = body[:fetch_end] + CALL + body[fetch_end:]
    out = head + PRELUDE + newbody
    assert out.count('\n') == src.count('\n'), 'el numero de lineas cambio!'
    with open(OUT, 'w', encoding='latin-1', newline='\n') as f:
        f.write(out)
    print('[+] escrito %s (%.2f MB), lineas: %d == original' % (
        OUT, len(out) / 1e6, out.count(chr(10))))


if __name__ == '__main__':
    main()
