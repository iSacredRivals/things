#!/usr/bin/env python3
"""Verificación de la key del user contra Luarmor (SDK público) + sondas API Quantum Onyx.
Replica EXACTAMENTE el flujo check_key de obf_2_clean.lua:
  GET sync -> nodos + st (server time)
  GET <nodo>check_key?key=<key>&script_id=<script_id>
      headers: clienttime=<st>, catcat128=hash(key.."_cfver1.0_"..script_id.."_time_"..st)
"""
import json, random, sys, urllib.request, urllib.error
sys.path.insert(0, "/home/z/my-project/deobf/aurora/scripts")
from catcat128 import catcat128

KEY = "LbdcJNWbjhlelJHknRFNRcbBzibDAyTl"
SCRIPT_ID = "0ae9fe4cf963e3a13d25eed0e2ce5940"
UA = "Roblox/WinInet"

def http(url, method="GET", headers=None, body=None, timeout=30):
    h = {"User-Agent": UA}
    if headers: h.update(headers)
    data = None
    if body is not None:
        data = body.encode() if isinstance(body, str) else body
    req = urllib.request.Request(url, method=method, headers=h, data=data)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")
    except Exception as e:
        return 0, f"ERROR: {e}"

print("=" * 70)
print("1) SYNC (sdkapi-public.luarmor.net)")
print("=" * 70)
st_code, st_body = http("https://sdkapi-public.luarmor.net/sync")
print(f"HTTP {st_code}")
try:
    sync = json.loads(st_body)
    print(json.dumps({k: v for k, v in sync.items() if k != "nodes"}, indent=2)[:500])
    nodes = sync.get("nodes", [])
    print(f"nodos ({len(nodes)}): {nodes[:4]}{'...' if len(nodes) > 4 else ''}")
except Exception as ex:
    print(f"No pude parsear sync: {ex}\n{st_body[:300]}")
    sync, nodes = {}, []

print()
print("=" * 70)
print("2) CHECK_KEY con la key del user")
print("=" * 70)
if nodes:
    node = random.choice(nodes)
    n_str = str(int(sync["st"])) if float(sync["st"]).is_integer() else str(sync["st"])
    url = node + "check_key?key=" + KEY + "&script_id=" + SCRIPT_ID
    cat = catcat128(KEY + "_cfver1.0_" + SCRIPT_ID + "_time_" + n_str)
    print(f"nodo elegido : {node}")
    print(f"clienttime   : {n_str}")
    print(f"catcat128    : {cat}")
    code, body = http(url, headers={"clienttime": n_str, "catcat128": cat})
    print(f"HTTP {code}")
    print(body[:2000])
else:
    print("sin nodos, salto")

print()
print("=" * 70)
print("3) SONDAS API QUANTUM ONYX (con x-qo-token del código vivo)")
print("=" * 70)
TOKEN = "secretkey-wqe231weqweqweqweqweqwe"
probe_body = json.dumps({"placeId": "2753915549", "jobId": ".x123.", "players": 1, "maxPlayers": 12})

probes = [
    ("POST /api/fullmoon (telemetría viva de Weebo)", "https://api.quantumonyx.cc/api/fullmoon", "POST",
     {"Content-Type": "application/json", "x-qo-token": TOKEN}, probe_body),
    ("POST /api/v1/authenticate + token", "https://api.quantumonyx.cc/api/v1/authenticate", "POST",
     {"Content-Type": "application/json", "x-qo-token": TOKEN},
     json.dumps({"key": KEY, "hwid": "390579c27946a14f06882047a90f2f90", "executor": "Delta", "game_id": 2753915549})),
    ("POST /api/v2/authenticate", "https://api.quantumonyx.cc/api/v2/authenticate", "POST",
     {"Content-Type": "application/json", "x-qo-token": TOKEN},
     json.dumps({"key": KEY, "hwid": "390579c27946a14f06882047a90f2f90", "executor": "Delta", "game_id": 2753915549})),
    ("POST /authenticate (sin version)", "https://api.quantumonyx.cc/authenticate", "POST",
     {"Content-Type": "application/json", "x-qo-token": TOKEN},
     json.dumps({"key": KEY, "hwid": "390579c27946a14f06882047a90f2f90", "executor": "Delta", "game_id": 2753915549})),
    ("GET  /docs (FastAPI docs)", "https://api.quantumonyx.cc/docs", "GET", {}, None),
    ("GET  /api/v1", "https://api.quantumonyx.cc/api/v1", "GET", {"x-qo-token": TOKEN}, None),
]
for label, url, method, headers, body in probes:
    code, resp = http(url, method=method, headers=headers, body=body, timeout=20)
    print(f"[{code}] {label} -> {resp[:200]}")
