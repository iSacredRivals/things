#!/usr/bin/env python3
"""
NEVAHEX V1 Deobfuscator - Todo en uno
Path sugerido: tools/nevahex_deobf.py
Uso: python tools/nevahex_deobf.py <archivo.luau>
"""
import sys, os, re, struct

# ========== TABLAS ==========

TABLE_2q = [130,194,127,29,227,180,95,203,52,193,104,100,121,138,249,35,81,243,1,77,85,25,208,64,16,90,58,32,71,245,21,54,42,140,116,144,191,0,205,149,124,142,75,87,213,99,48,103,44,189,128,210,5,30,67,37,229,109,55,69,97]
TABLE_5e = [43,254,239,111,200,237]
TABLE_1r = [175,151,74]
TABLE_0d = [114,177,89,102,40,246,6,10,57,125,20,139,101,230,2,108,207,15,46,175,133,118,209,166,94,4,129,24,84,119,82,231,212,12,86,233,9,182,106,187,179]
TABLE_5x = [76,36,252,192,224,140]
TABLE_5q = [215,9,129,166,50,53,155,255]
TABLE_0b = [173,158,10,123,123,187]
TABLE_1m = [68,131,206,221,56,198,51,132,98,115,74,170,7,76,62,79,143,176,224,174,53,219,45,197,181,36,172,214,237,80,14,137,91,247,185,112,18,78]
TABLE_3t = [63,105,235,34,151,171,22,13,157,23,169,28,159,161,123,242,228,11,43,8,38,186,244,50,47,27,154,239,70,88,184,199,66,202,251,238,113,65,195,255,122,217,248,107,253,188,241,222,240,162]
TABLE_2j = [153,183,236,120,61,49,190,134,200,3,215,135,59,211,178,216,196,218,19,60,163,141,93,250,17,232,158,252,165,145,225,110,234,126,33,31,168,204,117,92,192,96,41,254,164,156,150,152,39,223,146,147,226,26,167,155,111,201,73,72,220,136,173,148,83,160]

def build_1j():
    return TABLE_5e + TABLE_5x + TABLE_5q + TABLE_0b + TABLE_1r

def build_1h():
    return TABLE_1m + TABLE_2j + TABLE_0d + TABLE_3t + TABLE_2q

# ========== DECODIFICADORES ==========

def extract_base85(code):
    match = re.search(r'_2g\(\[=\[(.*?)\]=\]', code, re.DOTALL)
    if not match:
        raise ValueError("String base85 no encontrado")
    return match.group(1)

def decode_base85(s):
    s = re.sub(r'\s', '', s)
    s = s.replace('z', '!!!!!')
    result = bytearray()
    for i in range(0, len(s), 5):
        chunk = s[i:i+5]
        if len(chunk) < 5:
            chunk = chunk + '!' * (5 - len(chunk))
        d = ord(chunk[0]) - 33
        e = ord(chunk[1]) - 33
        f = ord(chunk[2]) - 33
        g = ord(chunk[3]) - 33
        h = ord(chunk[4]) - 33
        v = d * 52200625 + e * 614125 + f * 7225 + g * 85 + h
        result.extend(struct.pack('>I', v & 0xFFFFFFFF))
    return bytes(result[:31921])

def decode_5b(data):
    return bytes(data[i] ^ (((i+1)*46+61) & 0xFF) for i in range(len(data)))

def decode_2n(data):
    return bytes(data[i] ^ (((i+1)*71+182) & 0xFF) for i in range(len(data)))

def decode_0c(data):
    return bytes(data[i] ^ 56 for i in range(len(data)-1, -1, -1))

def decode_5r(data, _0n, _4c):
    _1g = len(_4c)
    result = bytearray()
    prev = 0
    for i in range(len(data)):
        enc = data[i]
        idx = i % _1g
        sub = (enc ^ _4c[idx]) ^ prev
        result.append(_0n[sub & 0xFF])
        prev = enc
    return bytes(result)

# ========== ANTI-TAMPERING ==========

def build_0n():
    return [x ^ 23 for x in build_1h()]

def build_4c():
    return [x ^ 35 for x in build_1j()]

def apply_4e(_0n, _4c):
    for i in range(256):
        _0n[i] ^= 0xAA
    for i in range(len(_4c)):
        _4c[i] = (_4c[i] + (i+1)) & 0xFF
    return _0n, _4c

def check_1b(_0n):
    return sum(_0n) % 65536 == 32640

def check_4j(_4c):
    r = 0
    for x in _4c:
        r ^= x
    return r == 1

def adler32(data):
    a, b = 1, 0
    for byte in data:
        a = (a + byte) % 65521
        b = (b + a) % 65521
    return (b * 65536 + a) & 0xFFFFFFFF

# ========== MAIN ==========

def deobfuscate(code):
    print("[*] NEVAHEX V1 Deobfuscator")
    
    # Estado 2436
    print("\n[2436] Decodificando base85...")
    b85 = extract_base85(code)
    _1n = decode_base85(b85)
    print(f"  Bytes: {len(_1n)}")
    
    # Construir tablas
    _0n = build_0n()
    _4c = build_4c()
    
    # Estado 534
    print("\n[534] Verificando checksums...")
    if not check_4j(_4c) or not check_1b(_0n):
        print("  Fallaron, aplicando _4e()")
        _0n, _4c = apply_4e(_0n, _4c)
    else:
        print("  OK")
    
    _3a = decode_5r(_1n, _0n, _4c)
    print(f"  _3a: {len(_3a)} bytes")
    
    # Estado 8271
    print("\n[8271] Verificando Adler32...")
    expected = 3118787290
    actual = adler32(_3a)
    print(f"  Esperado: {expected}")
    print(f"  Actual:   {actual}")
    
    if actual != expected:
        print("  Fallo, aplicando _4e() y re-decodificando...")
        _0n, _4c = apply_4e(_0n, _4c)
        _3a = decode_5r(_1n, _0n, _4c)
        actual = adler32(_3a)
        print(f"  Nuevo: {actual}")
    
    # Estado 9417
    print("\n[9417] Preparando payload...")
    _0j = 207 & 212  # 196
    _2s = 207 ^ 212  # 27
    cond = 2 * _0j + _2s  # 419
    print(f"  2*_0j+_2s = {cond}")
    
    if cond == 419:
        payload = _3a
    else:
        print("  Aplicando _2n()")
        payload = decode_2n(_3a)
    
    try:
        payload_str = payload.decode('utf-8', errors='replace')
    except:
        payload_str = payload.decode('latin-1')
    
    result = f"return function(_0kZ,...)\n{payload_str}\nend"
    
    print(f"\n[+] Payload: {len(result)} chars")
    print(f"[+] Primeros 300 chars:\n{result[:300]}")
    
    return result

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python nevahex_deobf.py <archivo.luau>")
        sys.exit(1)
    
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        code = f.read()
    
    result = deobfuscate(code)
    
    out = sys.argv[2] if len(sys.argv) >= 3 else 'output_deobfuscated.lua'
    with open(out, 'w', encoding='utf-8') as f:
        f.write(result)
    
    print(f"\n[+] Guardado en: {out}")
