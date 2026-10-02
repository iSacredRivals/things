#!/usr/bin/env python3
"""Construye el harness MITM de la cadena Luarmor completa:
stub (fresco, descargado live) -> bootstrapper (cache obf_4) -> loader (obf_5)
-> status -> key-check (key del user) -> PAYLOAD.

El harness corre en el env fiel de envlog (camuflaje C-closure etc.) y las
llamadas HTTP caen al __MITM: imprime \0MITM <N> <URL> y espera el archivo
mitm/resp_N.luau que escribe el driver (reenvio en vivo a los servers reales).
"""
import os, sys, re, urllib.request, urllib.error

HERE = "/home/z/my-project/deobf/aurora"
DEOBF = "/home/z/my-project/deobf/deobf"
sys.path.insert(0, DEOBF)
os.chdir(DEOBF)
import harness as H

MITM_DIR = HERE + "/analysis/replay/mitm"
os.makedirs(MITM_DIR, exist_ok=True)

KEY = "LbdcJNWbjhlelJHknRFNRcbBzibDAyTl"
STUB_URL = "https://api.luarmor.net/files/v4/loaders/0ae9fe4cf963e3a13d25eed0e2ce5940.lua"
BOOT_PATH = "static_content_170926/init-f07dbcbe19a-sephal.lua"

# ---------- 1) stub fresco ----------
print("[1] descargando stub fresco...")
req = urllib.request.Request(STUB_URL, headers={"User-Agent": "luau"})
with urllib.request.urlopen(req, timeout=30) as r:
    stub = r.read().decode("latin-1")
print(f"    stub: {len(stub)} bytes")
assert "_bsdata0" in stub, "stub sin _bsdata0?"


# P2D absurd values test
H.P2D_CACHE.update({
    "GetLength": "n:123.456",
    "GetPositionOnCurve|0.23076923191547394": "u:1,2,3,4",
    "GetPositionOnCurve|0.75": "u:1,2,3,4",
    "GetPositionOnCurve|0.5": "u:1,2,3,4",
    "GetTangentOnCurve|0.4444444477558136": "v:9,9",
    "GetTangentOnCurve|0.4166666567325552": "v:9,9",
    "GetTangentOnCurve|0.57142859697341919": "v:9,9",
    "GetTangentOnCurve|0.071428574621677399": "v:9,9",
    "GetPositionOnCurveArcLength|0.40000000596046448": "u:1,2,3,4",
    "GetPositionOnCurveArcLength|0.5": "u:1,2,3,4",
    "GetTangentOnCurveArcLength|0.55555558410546875": "v:9,9",
    "GetTangentOnCurveArcLength|0.5": "v:9,9",
})

# ---------- 2) chunks parcheados (VMC) ----------
def vmc_patch(src, mod=50000000):
    n = src.count("while true do")
    patched = "local __VMC=0\n" + src.replace(
        "while true do",
        "while true do __VMC+=1;if __VMC%%%d==0 then print('[VM] '..__VMC..' steps') end;" % mod)
    print(f"    vmc: {n} loops parcheados (mod {mod})")
    return patched

boot = open(HERE + "/extracted/obf_4.lua", "r", encoding="latin-1").read()
loader = open(HERE + "/extracted/obf_5.lua", "r", encoding="latin-1").read()
chunks = {
    H.chunk_key(boot): vmc_patch(boot),
    H.chunk_key(loader): vmc_patch(loader),
}

# ---------- 3) harness base ----------
print("[2] construyendo harness base...")
cfg = {
    "executor": "Delta",
    "time_budget": 5400,
    "max_stmts": 50000000,
    "heartbeat": 30,
    "prelude": (
        "genv.script_key = %r; rawset(G, 'script_key', %r); "
        "rawset(G, 'gethwid', function() return %r end); "
        "rawset(G, 'getexecutorname', function() return 'Delta' end)"
    ) % (KEY, KEY, "d3b14c1f2a9b7e8c4d5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c"),
}
base = H.build_harness(stub, cfg, chunks)
print(f"    harness base: {len(base)} bytes")

# ---------- 4) parches de texto ----------
print("[3] aplicando parches MITM...")

# 4a) embed del bootstrapper cacheado (antes del runtime envlog)
boot_lua = "local __BOOTFILE = " + H.long_string(boot) + "\n"
boot_lua += "local __BOOTPATH = " + H.lua_value(BOOT_PATH) + "\n"
# insertar justo antes del runtime: el runtime empieza tras las tablas __CHUNKS...
# busco el marcador de inicio del runtime: la linea local CFG / local R = {
marker = "local R = {\n"
idx = base.find(marker)
assert idx > 0, "marcador R no encontrado"
base = base[:idx] + boot_lua + base[idx:]

# 4b) funcion __MITM (despues de HTTPMAP, antes de httpMatch)
mitm_fn = '''
local __MITMN = 0
local function __MITM(label, url)
        if R.type(url) ~= "string" or url == "" then return nil end
        __MITMN += 1
        local n = __MITMN
        R.print("\\0MITM " .. n .. " " .. label .. " " .. url)
        -- espera la respuesta del driver (archivo mitm/resp_N.luau)
        local deadline = R.clock() + 240
        while R.clock() < deadline do
                local ok, body = pcall(require, "./mitm/resp_" .. n)
                if ok and R.type(body) == "string" then
                        R.print("\\0MITMDONE " .. n .. " " .. #body)
                        return body
                end
        end
        R.print("\\0MITMTIMEOUT " .. n)
        return nil
end
'''
anchor = "local function httpMatch(url)"
idx = base.find(anchor)
assert idx > 0, "ancla httpMatch no encontrada"
base = base[:idx] + mitm_fn + base[idx:]

# 4c) httpRequest fallback -> MITM
old = 'return callP(label .. "(" .. fmt(opts) .. ")", "response", "table")'
new = ('local __mb = __MITM(label, opts and opts.Url)\n'
       '\t\t\tif __mb ~= nil then return { Body = __mb, StatusCode = 200, Success = true, Headers = {} } end\n'
       '\t\t\treturn callP(label .. "(" .. fmt(opts) .. ")", "response", "table")')
assert base.count(old) == 1, f"httpRequest fallback: {base.count(old)}"
base = base.replace(old, new)

# 4d) namecall HttpGet fallback -> MITM
old = 'return callP(calleeText .. "(" .. fmtArgs(R.unpack(args, 1, args.n)) .. ")", "response", "string")'
new = ('local __mb = __MITM(name, R.type(a1) == "string" and a1 or (R.type(a1) == "table" and a1.Url))\n'
       '\t\t\tif __mb ~= nil then\n'
       '\t\t\t\tif R.type(a1) == "table" and (name == "RequestAsync" or name == "PostAsync") then\n'
       '\t\t\t\t\treturn { Body = __mb, StatusCode = 200, Success = true, Headers = {} }\n'
       '\t\t\t\tend\n'
       '\t\t\t\treturn __mb\n'
       '\t\t\tend\n'
       '\t\t\treturn callP(calleeText .. "(" .. fmtArgs(R.unpack(args, 1, args.n)) .. ")", "response", "string")')
assert base.count(old) == 1, f"namecall fallback: {base.count(old)}"
base = base.replace(old, new)

# 4e) readfile -> cache del bootstrapper
old = 'E.readfile = function(p) return callP("readfile(" .. fmt(p) .. ")", "contents", "string") end'
new = ('E.readfile = function(p)\n'
       '\tif R.type(p) == "string" and (p == __BOOTPATH or p:find(__BOOTPATH, 1, true)) then\n'
       '\t\tcomment("readfile(cache bootstrapper) -> " .. #__BOOTFILE .. " bytes")\n'
       '\t\treturn __BOOTFILE\n'
       '\tend\n'
       '\tcomment("readfile(" .. fmt(p) .. ") -> nil (no existe)")\n'
       '\treturn nil\n'
       'end')
assert base.count(old) == 1, f"readfile: {base.count(old)}"
base = base.replace(old, new)

# 4f) MAX_BLOCK enorme (el VM decode genera bloques larguisimos)
m = re.search(r"local MAX_BLOCK = CFG\.max_block or \d+", base)
assert m, "MAX_BLOCK no encontrado"
base = base.replace(m.group(0), "local MAX_BLOCK = 100000000")
print(f"    MAX_BLOCK: {m.group(0)} -> 100000000")

# 4g) isfile: el cache existe (para checks de isfolder/isfile del stub)
old = 'E.isfile = function(p) comment("isfile(" .. fmt(p) .. ") -> false"); return false end'
new = ('E.isfile = function(p)\n'
       '\tif R.type(p) == "string" and p:find("static_content_170926", 1, true) then\n'
       '\t\tcomment("isfile(" .. fmt(p) .. ") -> true")\n'
       '\t\treturn true\n'
       '\tend\n'
       '\tcomment("isfile(" .. fmt(p) .. ") -> false"); return false\n'
       'end')
if base.count(old) == 1:
    base = base.replace(old, new)
    print("    isfile parcheado")

out = MITM_DIR + "/mitm_test_p2d.luau"
with open(out, "w", encoding="latin-1", newline="\n") as f:
    f.write(base)
print(f"[4] harness escrito: {out} ({len(base)} bytes)")

# compila?
r = os.popen(f"{DEOBF}/bin/luau-compile --binary {out} > /dev/null 2> /tmp/mitm_compile_err.txt; echo $?").read().strip()
if r != "0":
    err = open("/tmp/mitm_compile_err.txt").read()[:800]
    print(f"[!] COMPILE ERROR:\n{err}")
    sys.exit(1)
print("[5] compile OK")
