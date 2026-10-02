#!/usr/bin/env python3
"""Recolector del bin de filebin del QO Premium Dumper.
Baja TODOS los archivos de filebin.net/<BIN> a /home/z/my-project/deobf/aurora/premium/"""
import json, os, sys, urllib.request

BIN = sys.argv[1] if len(sys.argv) > 1 else "qopremium-delta-01a"
OUT = "/home/z/my-project/deobf/aurora/premium"
os.makedirs(OUT, exist_ok=True)

def get(url, accept=None, timeout=60):
    h = {"User-Agent": "Mozilla/5.0"}
    if accept: h["Accept"] = accept
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read()

code, body = get(f"https://filebin.net/{BIN}", accept="application/json")
data = json.loads(body.decode())
files = data.get("files", [])
print(f"Bin {BIN}: {len(files)} archivos, {data.get('bin', {}).get('bytes_readable', '?')}")

for f in files:
    fname = f["filename"]
    size = f["bytes"]
    # saltar los que ya tengo con el mismo md5/size
    dest = os.path.join(OUT, fname)
    if os.path.exists(dest) and os.path.getsize(dest) == size:
        print(f"  = {fname} ({size} B) ya existe")
        continue
    try:
        code, content = get(f"https://filebin.net/{BIN}/{fname}")
        with open(dest, "wb") as fh:
            fh.write(content)
        print(f"  + {fname} ({len(content)} B)")
    except Exception as e:
        print(f"  ! {fname}: {e}")

print(f"\nListo -> {OUT}")
