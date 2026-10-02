#!/usr/bin/env python3
"""Sonda check_key v3 con matriz de headers — ver como evoluciona el error."""
import json, random, sys, urllib.request, urllib.error
sys.path.insert(0, "/home/z/my-project/deobf/aurora/scripts")
from catcat128 import catcat128

KEY = "LbdcJNWbjhlelJHknRFNRcbBzibDAyTl"
SCRIPT_ID = "0ae9fe4cf963e3a13d25eed0e2ce5940"

def http(url, headers=None, timeout=20):
    h = {"User-Agent": "luau"}
    if headers:
        h.update(headers)
        if "User-Agent" in headers:
            h["User-Agent"] = headers["User-Agent"]
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")
    except Exception as e:
        return 0, f"ERROR: {e}"

# sync fresco
code, body = http("https://sdkapi-public.luarmor.net/sync")
print(f"sync: HTTP {code} :: {body[:150]}")
sync = json.loads(body)
nodes = sync["nodes"]
st = int(sync["st"])
node = random.choice(nodes)

combos = [
    ("sin nada, UA luau",        {"User-Agent": "luau"}),
    ("sin nada, UA Roblox/WinInet", {"User-Agent": "Roblox/WinInet"}),
    ("hwid 32hex, UA luau",      {"User-Agent": "luau", "hwid": "d3b14c1f2a9b7e8c4d5f6a7b8c9d0e1f"}),
    ("hwid 64hex, UA luau",      {"User-Agent": "luau", "hwid": "d3b14c1f2a9b7e8c4d5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c"}),
    ("hwid+executor Delta",      {"User-Agent": "luau", "hwid": "d3b14c1f2a9b7e8c4d5f6a7b8c9d0e1f", "executor": "Delta"}),
    ("Fingerprint 32hex",        {"User-Agent": "luau", "Fingerprint": "d3b14c1f2a9b7e8c4d5f6a7b8c9d0e1f"}),
    ("hwid guiones",             {"User-Agent": "luau", "hwid": "D3B1-4C1F-2A9B-7E8C-4D5F-6A7B"}),
]

for name, hdrs in combos:
    # clienttime y catcat128 con st fresco
    hdrs2 = dict(hdrs)
    hdrs2["clienttime"] = str(st)
    hdrs2["catcat128"] = catcat128(KEY + "_cfver1.0_" + SCRIPT_ID + "_time_" + str(st))
    url = node + "check_key?key=" + KEY + "&script_id=" + SCRIPT_ID
    code, body = http(url, hdrs2)
    print(f"[{name}] HTTP {code} :: {body[:220]}")
    # refrescar st cada vez (el server time avanza)
    code2, body2 = http("https://sdkapi-public.luarmor.net/sync")
    if code2 == 200:
        try:
            st = int(json.loads(body2)["st"])
        except Exception:
            pass
