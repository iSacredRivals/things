#!/usr/bin/env python3
"""Replay de la cadena Luarmor capturada en el Delta del usuario.

Entrada (workspace_zip/):
  qodump_01  stub con _bsdata0 NUEVO (el que corrio en Delta)
  qodump_03  bootstrapper V4 (764 KB)  == extracted/obf_4.lua
  qodump_04..07  respuestas reales de x.luarmor.net (payload cifrado)
  qodump_09  status de us1-roblox-auth.luarmor.net

Corre el bootstrapper en el harness con un router HTTP que sirve las
respuestas capturadas EN ORDEN, instala la key del usuario y hace dump
inmediato por stdout de toda fuente >= 4 KB que pase por loadstring.
"""
import os
import re
import sys

sys.path.insert(0, "deobf")
import harness as H  # noqa: E402

BASE = "aurora_qo"
WS = os.path.join(BASE, "workspace_zip")
EXTR = os.path.join(BASE, "extracted")
OUT = os.path.join(BASE, "analysis", "replay")
os.makedirs(OUT, exist_ok=True)

KEY = "LbdcJNWbjhlelJHknRFNRcbBzibDAyTl"
PLACE_ID = 2753915549  # Blox Fruits
LUAU = H.find_luau()


def rd(p):
    with open(p, encoding="latin-1") as f:
        return f.read()


def ls(s):
    lvl = 0
    while ("]" + "=" * lvl + "]") in s:
        lvl += 1
    # "]]" se auto-solapa: un cuerpo que TERMINA en "]" se fusionaria con el
    # closer de nivel 0 y cerraria un caracter antes. Nivel >= 1 es inmune.
    if lvl == 0 and s.endswith("]"):
        lvl = 1
    eq = "=" * lvl
    return "[" + eq + "[\n" + s + "]" + eq + "]"


# ---------------------------------------------------------------- archivos
stub = rd(os.path.join(WS, "qodump_1790732004_01_api.luarmor.net_files_v4_loaders_0ae9fe4cf963e"))
m = re.search(r"_bsdata0\s*=\s*(\{.*?\});", stub, re.S)
assert m, "no _bsdata0 en stub"
bsdata = m.group(1)

resp = {}
for n in ("04", "05", "06", "07", "09"):
    pat = next(p for p in os.listdir(WS)
               if p.startswith(f"qodump_1790732004_{n}_") and not p.endswith(".meta"))
    resp[n] = rd(os.path.join(WS, pat))
    print(f"[*] resp{n}: {len(resp[n])} B  <- {pat}")

boot = rd(os.path.join(EXTR, "obf_4.lua"))
assert ":TK()(...)" in boot, "no encuentro :TK()(...) en obf_4"
boot = boot.replace(":TK()(...)", ':TK()("f07dbcbe19a-sephal")', 1)

sync_body = '{"nodes":["https://sdkapi-public.luarmor.net/"],"st":%d}' % 1790732050
check_key_body = ('{"success":true,"message":"Key authorized","key":{"key":"%s","status":"active"'
                  ',"expiration":1799999999},"scriptData":{},"script":{"id":"0ae9fe4cf963e3a13d25'
                  'eed0e2ce5940","name":"bloxfruits","version":"0056"}}') % KEY

# ---------------------------------------------------------------- prelude
prelude = f"""-- replay prelude: entorno del stub + router HTTP por orden + dump loadstring
rawset(G, "_bsdata0", {bsdata})
rawset(G, "ldrupd8m", nil)
genv.script_key = "{KEY}"
shared.script_key = "{KEY}"
setprop(game, "PlaceId", {PLACE_ID})
local env = env
local responses = {{{ls(resp["04"])}, {ls(resp["05"])}, {ls(resp["06"])}, {ls(resp["07"])}}}
local statusbody = {ls(resp["09"])}
local nreq = 0
local function serve(url)
  if env.type(url) ~= "string" then return nil end
  if env.string.find(url, "x.luarmor.net", 1, true) then
    nreq = nreq + 1
    env.print("[REPLAY-HTTP] x.luarmor.net #" .. nreq)
    local b = responses[nreq]
    if b then return {{Body = b, StatusCode = 200, Success = true, Headers = {{}}}} end
    env.print("[REPLAY-HTTP] !! sin respuesta capturada para: " .. url)
    return nil
  end
  if env.string.find(url, "us1-roblox-auth.luarmor.net/status", 1, true) then
    env.print("[REPLAY-HTTP] status -> grabada")
    return {{Body = statusbody, StatusCode = 200, Success = true, Headers = {{}}}}
  end
  return nil
end
local function wrapfn(f)
  return function(req)
    local url = env.type(req) == "table" and req.Url or req
    local r = serve(url)
    if r then return r end
    return f(req)
  end
end
rawset(env, "request", wrapfn(env.request))
rawset(env, "http_request", wrapfn(env.http_request))
if env.type(env.http) == "table" and env.type(env.http.request) == "function" then
  env.http.request = wrapfn(env.http.request)
end
if env.type(env.syn) == "table" and env.type(env.syn.request) == "function" then
  env.syn.request = wrapfn(env.syn.request)
end
local origls = env.loadstring
rawset(env, "loadstring", function(src, cn)
  if env.type(src) == "string" and #src >= 4096 then
    env.print("\\n\\0REPLAYLS " .. env.tostring(#src) .. " " .. env.tostring(cn) .. "\\n" .. src .. "\\n\\0REPLAYLSEND\\n")
  end
  return origls(src, cn)
end)
"""

# ---------------------------------------------------------------- cfg
http_map = [
    "cdn.luarmor.net/v4_init_sephal", boot,
    "d=929c04812ef86e", resp["04"],
    "d=3f1863b183c7fe", resp["05"],
    "d=4965dbdba94250", resp["06"],
    "d=fc92fbc3419fa6", resp["07"],
    "us1-roblox-auth.luarmor.net/status", resp["09"],
    "sdkapi-public.luarmor.net/sync", sync_body,
    "check_key?key=", check_key_body,
]

cfg = {
    "prelude": prelude,
    "http_responses": http_map,
    "time_budget": 180,
    "executor": "Delta",
    "spin": 12,
    "heartbeat": 0,
    "stackdump": True,
}

hpath = os.path.join(OUT, "harness_round1.luau")
print(f"[*] luau: {LUAU}")
print(f"[*] corriendo bootstrapper V4 ({len(boot)} B) con respuestas reales...")
body, err = H.run_once(LUAU, boot, cfg, hpath, timeout=420, keep=True, chunks=None)
H.save_raw(os.path.join(OUT, "raw_round1.txt"))

print("\n========== RESULTADO ==========")
if body is None:
    print("[-] run fallo / timeout. Cola del raw:")
    print((H.LAST_RAW[0] or "")[-4000:])
else:
    print(f"[+] trace OK ({len(body)} chars)")

# chunks reportados por envlog
chunks, body_clean = H.take_chunks(body or "")
for k, src in chunks:
    p = os.path.join(OUT, f"chunk_{k}.lua")
    with open(p, "w", encoding="latin-1") as f:
        f.write(src)
    print(f"[+] CHUNK {k}: {len(src)} B -> {p}")
    print(f"    head: {src[:120]!r}")

# dumps inmediatos por stdout (REPLAYLS) — cubre el caso de timeout
raw = H.LAST_RAW[0] or ""
ls_dumps = re.findall(r"\x00REPLAYLS (\d+) ([^\n]*)\n(.*?)\n\x00REPLAYLSEND", raw, re.S)
for i, (sz, cn, src) in enumerate(ls_dumps):
    p = os.path.join(OUT, f"replayls_{i}_{sz}B.lua")
    with open(p, "w", encoding="latin-1") as f:
        f.write(src)
    print(f"[+] REPLAYLS #{i}: {sz} B (chunkname={cn.strip()!r}) -> {p}")
    print(f"    head: {src[:120]!r}")

# log de URLs y errores
urls = sorted(set(re.findall(r"\[REPLAY-HTTP\][^\n]*", raw)))
print(f"\n[*] hits del router: {len(urls)} distintos")
for u in urls[:20]:
    print("   " + u)
reqs = re.findall(r"request\(\{Url = \"([^\"]+)\"", body or "")
if reqs:
    print("[*] URLs solicitadas (envlog):")
    for u in sorted(set(reqs))[:30]:
        print("   " + u[:160])
if err:
    print("\n[-] ERROR:", str(err)[:2000])
