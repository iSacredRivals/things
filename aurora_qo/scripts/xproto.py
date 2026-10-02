#!/usr/bin/env python3
"""Analiza el protocolo x.luarmor.net:
- v1 respuestas 04..07 (JSON arrays de chunks) -> ensamblan obf_5 (known plaintext)
- deriva el cifrado de los chunks hex
- decodifica respuestas 04 (handshake) de v1 y v2
"""
import json, sys, binascii, os

BASE = "/home/z/my-project/deobf/aurora"
W1 = BASE + "/workspace_zip"           # capturas v1
W2 = BASE + "/workspacee_zip/extracted"  # capturas v2

v1_files = [
    W1 + "/qodump_1790732004_04_x.luarmor.net_a9b90889ea88d2a9cfaac_a_fa6607_d",
    W1 + "/qodump_1790732004_05_x.luarmor.net_a9b90889ea88d2a9cfaac_a_fa6607_d",
    W1 + "/qodump_1790732004_06_x.luarmor.net_a9b90889ea88d2a9cfaac_a_fa6607_d",
    W1 + "/qodump_1790732004_07_x.luarmor.net_a9b90889ea88d2a9cfaac_a_fa6607_d",
]
obf5 = open(BASE + "/extracted/obf_5.lua", "rb").read()
v2_04 = open(W2 + "/qodump2_1790739219_04_x.luarmor.net_a9b90889ea88d2a9cfaac_a_fa6607_d", "rb").read()

print(f"obf_5 = {len(obf5)} bytes")

def is_hex(s: str) -> bool:
    if len(s) == 0 or len(s) % 2 != 0:
        return False
    try:
        int(s, 16)
        return True
    except ValueError:
        return False

# ---- parse v1 responses ----
responses = []
for i, f in enumerate(v1_files):
    data = open(f, "rb").read().decode("utf-8", "replace")
    try:
        arr = json.loads(data)
    except Exception as e:
        print(f"[{i}] JSON error: {e}; head: {data[:120]!r}")
        arr = None
    responses.append(arr)
    if arr is not None:
        hexc = [c for c in arr if isinstance(c, str) and is_hex(c)]
        plain = [c for c in arr if isinstance(c, str) and not is_hex(c)]
        print(f"[{i+4:02d}] items={len(arr)} hex={len(hexc)} plain={len(plain)} "
              f"hexbytes={sum(len(h)//2 for h in hexc)} plainbytes={sum(len(p) for p in plain)}")
        # tipos raros
        types = {}
        for c in arr:
            types[type(c).__name__] = types.get(type(c).__name__, 0) + 1
        if set(types) != {"str"}:
            print(f"      tipos: {types}")
        # muestra
        for j, c in enumerate(arr[:8]):
            kind = "HEX" if (isinstance(c, str) and is_hex(c)) else ("STR" if isinstance(c, str) else f"INT={c}")
            s = c[:80] if isinstance(c, str) else str(c)
            print(f"      [{j}] {kind} len={len(c) if isinstance(c,str) else '?'} :: {s!r}")
        if len(arr) > 8:
            for j, c in enumerate(arr[-3:]):
                kind = "HEX" if (isinstance(c, str) and is_hex(c)) else ("STR" if isinstance(c, str) else f"INT={c}")
                s = c[:80] if isinstance(c, str) else str(c)
                print(f"      [tail{j}] {kind} len={len(c) if isinstance(c,str) else '?'} :: {s!r}")

# ---- ensamblar stream: hex -> bytes decodificados, plain -> bytes directos ----
def assemble(arr):
    out = bytearray()
    marks = []  # (offset_in_out, chunk_index, is_hex)
    for idx, c in enumerate(arr):
        if isinstance(c, str) and is_hex(c):
            b = binascii.unhexlify(c)
            marks.append((len(out), idx, True))
            out += b
        elif isinstance(c, str):
            marks.append((len(out), idx, False))
            out += c.encode("latin-1", "replace")
    return bytes(out), marks

total = bytearray()
allmarks = []
for arr in responses[1:]:  # 05,06,07 (04 es handshake aparte)
    if arr is None:
        continue
    b, m = assemble(arr)
    allmarks.extend((len(total) + off, idx, hx) for off, idx, hx in m)
    total += b

print(f"\nensamblado 05+06+07 = {len(total)} bytes vs obf_5 = {len(obf5)} bytes")
# compara prefijo
n = min(len(total), len(obf5))
same = 0
for i in range(n):
    if total[i] != obf5[i]:
        break
    same += 1
print(f"prefijo común = {same} bytes ({same/n*100:.1f}%)")

if same < 50:
    # prueba: ensamblar solo plain, solo hex-decod, u otro orden
    print("\n[!] no coincide directo; probando variantes...")
    plain_only = bytearray()
    for arr in responses[1:]:
        if arr is None: continue
        for c in arr:
            if isinstance(c, str) and not is_hex(c):
                plain_only += c.encode("latin-1", "replace")
    print(f"  solo-plain = {len(plain_only)}")
    hexonly = bytearray()
    for arr in responses[1:]:
        if arr is None: continue
        for c in arr:
            if isinstance(c, str) and is_hex(c):
                hexonly += binascii.unhexlify(c)
    print(f"  solo-hexdec = {len(hexonly)}  head: {bytes(hexonly[:60])!r}")

    # posiblemente cada chunk hex es cifrado que hay que descifrar con stream del handshake
    # guardar artefactos para analisis manual
    open(BASE + "/analysis/xproto_ensamblado.bin", "wb").write(bytes(total))
    open(BASE + "/analysis/xproto_ensamblado_plainonly.bin", "wb").write(bytes(plain_only))
    print("  artefactos guardados en analysis/xproto_*.bin")

# si coincide en prefijo, deriva keystream de los chunks hex
if same >= 50:
    print("\n[+] ensamblado == obf_5 (prefix). Derivando keystream de chunks hex:")
    # encontrar donde diverge (si diverge)
    div = None
    for i in range(n):
        if total[i] != obf_5[i]:
            div = i
            break
    print(f"  primera divergencia: {div}")
    # keystream: para cada chunk hex en offset o: ks = cipher ^ plain
    ks_pairs = []
    for off, idx, hx in allmarks:
        if not hx:
            continue
        ln = 0
        # longitud del chunk
        arr_idx = None
        # recomputar longitud via marks siguiente
        pass
    # recomputo longitudes
    offs = [(off, idx, hx) for off, idx, hx in allmarks if hx]
    lens = {}
    for k, (off, idx, hx) in enumerate(offs):
        end = offs[k+1][0] if k+1 < len(offs) else len(total)
        lens[idx] = (off, end - off)
    keystream = {}
    for idx, (off, ln) in lens.items():
        cip = total[off:off+ln]
        pla = obf5[off:off+ln]
        ks = bytes(a ^ b for a, b in zip(cip, pla))
        keystream[idx] = (off, ln, ks)
        print(f"  chunk[{idx}] off={off} len={ln} ks[:24]={ks[:24].hex()}")
    # guardar
    with open(BASE + "/analysis/xproto_keystream.bin", "wb") as f:
        for idx in sorted(keystream):
            f.write(keystream[idx][2])
    import json as J
    with open(BASE + "/analysis/xproto_ks_map.json", "w") as f:
        J.dump({str(k): [v[0], v[1], v[2].hex()] for k, v in keystream.items()}, f, indent=1)
    print("  keystream guardado: analysis/xproto_keystream.bin + mapa json")

    # ---- aplicar keystream (si es estatico desde offset 0) a la respuesta 04 ----
    print("\n=== decodificar handshake 04 (v2) ===")
    arr = json.loads(v2_04)
    print(f"items 04-v2: {len(arr)}")
    ks = open(BASE + "/analysis/xproto_keystream.bin", "rb").read()
    for c in arr:
        if is_hex(c):
            b = binascii.unhexlify(c)
            dec = bytes(x ^ ks[i % len(ks)] for i, x in enumerate(b))
            print(f"  XOR-ks estatico: {dec[:200]!r}")
            # tambien probar con offset 0 exacto (sin modulo)
            dec2 = bytes(x ^ ks[i] for i, x in enumerate(b) if i < len(ks))
            print(f"  XOR-ks exacto:   {dec2[:200]!r}")
