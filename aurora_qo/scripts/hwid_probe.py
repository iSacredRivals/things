#!/usr/bin/env python3
"""Sonda de formatos de header hwid/UA para el check_key de Luarmor.
El executor (Delta etc.) inyecta hwid en cada request; el server valida el FORMATO
para identificar el executor. Probamos combinaciones hasta pasar la validación."""
import json, random, sys, urllib.request, urllib.error
sys.path.insert(0, "/home/z/my-project/deobf/aurora/scripts")
from catcat128 import catcat128

KEY = "LbdcJNWbjhlelJHknRFNRcbBzibDAyTl"
SCRIPT_ID = "0ae9fe4cf963e3a13d25eed0e2ce5940"

def http(url, method="GET", headers=None, timeout=20):
    h = {"User-Agent": "Roblox/WinInet"}
    if headers:
        h.update(headers)
        if "User-Agent" in headers:
            h["User-Agent"] = headers["User-Agent"]
    req = urllib.request.Request(url, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode(errors="replace"), dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace"), dict(e.headers)
    except Exception as e:
        return 0, f"ERROR: {e}", {}

# sync fresco (con reintentos)
sync = None
for attempt in range(4):
    code, body, _ = http("https://sdkapi-public.luarmor.net/sync")
    print(f"sync intento {attempt+1}: HTTP {code} len={len(body)} {body[:80]}")
    if code == 200 and body.strip().startswith("{"):
        sync = json.loads(body)
        break
    import time as _t; _t.sleep(2)
if not sync:
    print("SYNC FALLA — aborto")
    sys.exit(1)
nodes = sync["nodes"]
node = nodes[0]
st = int(sync["st"])
cat = catcat128(KEY + "_cfver1.0_" + SCRIPT_ID + "_time_" + str(st))
print(f"sync OK (st={st}), nodo: {node}")

import binascii, uuid
hwids = {
    "32hex":        binascii.hexlify(b"0123456789abcdef"[:16]).decode()[:32],
    "64hex":        "a" * 64,
    "guid":         str(uuid.uuid5(uuid.NAMESPACE_DNS, "delta-hwid")),
    "delta-like":   "DELTA-" + binascii.hexlify(b"xyz123").decode().upper(),
    "numeric":      "1234567890123456789",
}
uas = ["Roblox/WinInet", "Delta", "Roblox/Delta", "Hydrogen", "Mozilla/5.0"]

base_h = {"clienttime": str(st), "catcat128": cat}
results = {}
for hname, hval in hwids.items():
    for ua in uas:
        h = dict(base_h)
        h["hwid"] = hval
        h["User-Agent"] = ua
        code, body, rh = http(node + "check_key?key=" + KEY + "&script_id=" + SCRIPT_ID, headers=h)
        tag = "PASS" if "INVALID_EXECUTOR" not in body else "reject"
        if tag == "PASS":
            print(f"*** PASS: hwid={hname} ua={ua} -> HTTP {code} {body[:300]}")
            results[(hname, ua)] = body
        else:
            msg = body[:120]
            # distinto mensaje de rechazo = progreso
            if "invalid" not in msg.lower() or "hwid" not in msg.lower():
                print(f"    {hname}/{ua}: HTTP {code} {msg}")
if not results:
    print("\nNingún combo pasó. Últimos cuerpos de rechazo:")
    h = dict(base_h); h["hwid"] = hwids["32hex"]; h["User-Agent"] = "Delta"
    print(http(node + "check_key?key=" + KEY + "&script_id=" + SCRIPT_ID, headers=h)[1][:300])
