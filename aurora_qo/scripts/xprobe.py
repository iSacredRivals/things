#!/usr/bin/env python3
"""Sonda: reintentar las URLs capturadas de x.luarmor.net desde el server.
Si el server las acepta, el replay MITM en vivo es viable.
"""
import urllib.request, urllib.error, ssl, time

W1 = "/home/z/my-project/deobf/aurora/workspace_zip"
W2 = "/home/z/my-project/deobf/aurora/workspacee_zip/extracted"

def get_url_from_meta(metafile):
    txt = open(metafile, "r", errors="replace").read()
    for line in txt.split("\n"):
        if line.startswith("url="):
            return line[4:].strip()
    return None

probes = []
# v2 handshake (la mas fresca)
probes.append(("v2-04 (fresca, c param)", get_url_from_meta(W2 + "/qodump2_1790739219_04_x.luarmor.net_a9b90889ea88d2a9cfaac_a_fa6607_d.meta")))
# v1 handshake
probes.append(("v1-04 (vieja)", get_url_from_meta(W1 + "/qodump_1790732004_04_x.luarmor.net_a9b90889ea88d2a9cfaac_a_fa6607_d.meta")))
# v1 parts
for i in ["05", "06", "07"]:
    probes.append((f"v1-{i} (parts)", get_url_from_meta(W1 + f"/qodump_1790732004_{i}_x.luarmor.net_a9b90889ea88d2a9cfaac_a_fa6607_d.meta")))

UA = "luau"
ctx = ssl.create_default_context()

for name, url in probes:
    if not url:
        print(f"[{name}] sin URL"); continue
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
            body = r.read()
            print(f"[{name}] HTTP {r.status} len={len(body)} t={time.time()-t0:.1f}s :: {body[:100]!r}")
    except urllib.error.HTTPError as e:
        body = e.read()
        print(f"[{name}] HTTP {e.code} len={len(body)} :: {body[:200]!r}")
    except Exception as e:
        print(f"[{name}] ERROR: {e}")

# extra: request con URL base (sin params) para ver el comportamiento
print("\n--- sonda path base ---")
for u in ["https://x.luarmor.net/a9b90889ea88d2a9cfaac", "https://x.luarmor.net/a9b90889ea88d2a9cfaac?a=fa6607"]:
    try:
        req = urllib.request.Request(u, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
            print(f"[{u[-30:]}] HTTP {r.status} :: {r.read()[:150]!r}")
    except urllib.error.HTTPError as e:
        print(f"[{u[-30:]}] HTTP {e.code} :: {e.read()[:200]!r}")
    except Exception as e:
        print(f"[{u[-30:]}] ERROR: {e}")
