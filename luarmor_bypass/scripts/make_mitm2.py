#!/usr/bin/env python3
"""Construye el harness MITM de la cadena Luarmor completa:
stub (fresco, descargado live) -> bootstrapper (cache obf_4) -> loader (obf_5)
-> status -> key-check (key del user) -> PAYLOAD.

El harness corre en el env fiel de envlog (camuflaje C-closure etc.) y las
llamadas HTTP caen al __MITM: imprime \0MITM <N> <URL> y espera el archivo
mitm/resp_N.luau que escribe el driver (reenvio en vivo a los servers reales).
"""
import os, sys, re, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))          # .../luarmor_bypass/scripts
BYPASS = os.path.dirname(HERE)                              # .../luarmor_bypass (v4_init.lua)
PKG = os.path.dirname(BYPASS)                               # .../<raiz del paquete>
DEOBF = os.path.join(PKG, "deobf")
sys.path.insert(0, DEOBF)
os.chdir(DEOBF)
import harness as H

MITM_DIR = HERE + "/mitm"
os.makedirs(MITM_DIR, exist_ok=True)

KEY = "uheDAutILiYSgLDdOGYOZLEghHghjvqA"
HWID = "d3b14c1f2a9b7e8c4d5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c"
STUB_URL = "https://api.luarmor.net/files/v3/loaders/479e9f38148118df2d14fc0795ece576.lua"
BOOT_PATH = "static_content_170926/init-f07dbcbe19a-sephal.lua"

# ---------- 1) stub fresco ----------
print("[1] descargando stub fresco...")
req = urllib.request.Request(STUB_URL, headers={"User-Agent": "luau"})
with urllib.request.urlopen(req, timeout=30) as r:
    stub = r.read().decode("latin-1")
print(f"    stub: {len(stub)} bytes")
assert "_bsdata0" in stub, "stub sin _bsdata0?"

# SIMULAR EL PATH DE DESCARGA (v1): en la primera corrida del device el stub
# bajo el bootstrapper del CDN: seteo ldrupd8m=<string> y llamo loadstring(a)(b)
# CON el arg b. El path de cache hace a() sin arg ni ldrupd8m; combinado con
# la ausencia del json de sesion mataba el VM en string.sub(nil).
old1 = "if a and #a>2000 then a=loadstring(a) else a=nil; end;"
new1 = "if a and #a>2000 then ldrupd8m=a; a=loadstring(a) else a=nil; end;"
if old1 in stub:
    stub = stub.replace(old1, new1, 1)
    print("    stub: ldrupd8m=a (path descarga simulado)")
old2 = "if a then return a() else"
new2 = "if a then return a(b) else"
if old2 in stub:
    stub = stub.replace(old2, new2, 1)
    print("    stub: a(b) con arg (path descarga simulado)")

# loader P2D cache (L2D): los valores de la sonda del LOADER (probe2 del user).
# Placeholder: copia del bootstrapper hasta que llegue apply_p2d2.py
L2D_DATA = {'GetLength': 'n:269.48037719726562', 'GetPositionOnCurve|0.75': 'u:0.059545014053583145,0,0.1060267835855484,0', 'GetPositionOnCurve|0.5': 'u:0.1843830943107605,0,0.1629464328289032,0', 'GetPositionOnCurve|0.8461538553237915': 'u:0.12837627530097961,0,0.17614112794399261,0', 'GetTangentOnCurve|0.75': 'v:-27.6875,-66', 'GetTangentOnCurve|0.5': 'v:-42.890625,49.5', 'GetTangentOnCurve|0.18181818723678589': 'v:-9.0625,15', 'GetPositionOnCurveArcLength|0.40000000596046448': 'u:0.13498768210411072,0,0.20871745049953461,0', 'GetPositionOnCurveArcLength|0.28571429848670959': 'u:0.23828420042991638,0,0.10412024706602097,0', 'GetTangentOnCurveArcLength|0.8571428656578064': 'v:61.598293304443359,105.97488403320312', 'GetTangentOnCurveArcLength|0.69999998807907104': 'v:95.972557067871094,151.43309020996094'}
H.P2D_CACHE.update({'GetLength': 'n:276.96829223632812', 'GetPositionOnCurve|0.23076923191547394': 'u:0.20893269777297974,0,0.20536212623119354,0', 'GetPositionOnCurve|0.75': 'u:0.33657625317573547,0,0.3415798544883728,0', 'GetPositionOnCurve|0.5': 'u:0.53144651651382446,0,0.4895833432674408,0', 'GetTangentOnCurve|0.4444444477558136': 'v:60.148139953613281,85.074058532714844', 'GetTangentOnCurve|0.4166666567325592': 'v:79.583328247070312,121.91665649414062', 'GetTangentOnCurve|0.57142859697341919': 'v:-27.336761474609375,-86.142860412597656', 'GetTangentOnCurve|0.071428574621677399': 'v:63.061225891113281,96.122451782226562', 'GetPositionOnCurveArcLength|0.40000000596046448': 'u:0.34185576438903809,0,0.32872346043586731,0', 'GetPositionOnCurveArcLength|0.5': 'u:0.44132214784622192,0,0.41902029514312744,0', 'GetTangentOnCurveArcLength|0.55555558204650879': 'v:65.504676818847656,95.221893310546875', 'GetTangentOnCurveArcLength|0.5': 'v:99.690704345703125,160.12794494628906'})

# ---------- 2) chunks parcheados (VMC) ----------
def vmc_patch(src, mod=50000000):
    n = src.count("while true do")
    patched = "local __VMC=0\n" + src.replace(
        "while true do",
        "while true do __VMC+=1;if __VMC%%%d==0 then print('[VM] '..__VMC..' steps') end;" % mod)
    print(f"    vmc: {n} loops parcheados (mod {mod})")
    return patched

boot = open(os.path.join(BYPASS, "v4_init.lua"), "r", encoding="latin-1").read()
assert ":TK()(...)" in boot, "no encuentro :TK()(...) en v4_init"
# chunks: SOLO el bootstrapper (universal, byte-identico verificado MD5).
# El LOADER de ESTE script llega NUEVO desde el server (respuestas en vivo):
# no se pre-registra ningun chunk de loader.
chunks = {
    H.chunk_key(boot): vmc_patch(boot),
}

# ---------- 3) harness base ----------
print("[2] construyendo harness base...")
def lua_table_str(d):
    parts = []
    for k, v in d.items():
        parts.append("[%r] = %r" % (k, v))
    return "{" + ", ".join(parts) + "}"

L2D_DATA_LUA = lua_table_str(L2D_DATA)
cfg = {
    "executor": "Delta",
    "time_budget": 5400,
    "max_stmts": 50000000,
    "heartbeat": 30,
    "ptrace": True,
    "gsub_dump": True,
    # OJO: el prelude corre con env = E = ENV (la tabla de globales REAL del
    # chunk). rawset(G,...)/genv.x escriben en _G/getgenv() FALSOS y el VM
    # lee el global desnudo -> caia al proxy "No key found". Fix: env.script_key.
    # El KEYSYSTEM (obf_1) setea TODOS estos antes del LoadStockLoader:
    # ApplyScriptKey: getgenv().script_key + getgenv().key + _G + shared
    # y tras VerifyWithServer: key_expire, key_note, key_executions.
    "prelude": (
        "rawset(env, '__L2D', %s); "
        "genv.script_key = %r; rawset(G, 'script_key', %r); "
        "rawset(env, 'script_key', %r); "
        "genv.key = %r; rawset(G, 'key', %r); rawset(env, 'key', %r); "
        "genv.key_expire = 0; genv.key_note = ''; genv.key_executions = 0; "
        "rawset(env, 'gethwid', function() return %r end); "
        "rawset(env, 'getexecutorname', function() return 'Delta' end); "
        "rawset(shared, 'script_key', %r); rawset(shared, 'key', %r)"
    ) % (L2D_DATA_LUA, KEY, KEY, KEY, KEY, KEY, KEY, HWID, KEY, KEY),
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
# Sin io en el luau CLI: canal = prints \0-tagged + PADDING de 8KB que fuerza
# el flush del buffer de stdout (verificado: el log recibe la linea al instante)
# + el driver escribe mitm/resp_N.luau y el harness lo levanta con require
# (verificado: poll-require levanta archivos creados a mitad del loop).
mitm_fn = '''
local __MITMN = 0
local __PAD = R.rep("P", 8192)
local function __MITM(label, url, opts)
        if R.type(url) ~= "string" or url == "" then
                if R.type(opts) == "table" and R.type(opts.Url) == "string" then url = opts.Url end
        end
        if R.type(url) ~= "string" or url == "" then return nil end
        __MITMN += 1
        local n = __MITMN
        -- metodo/body/headers del request completo (body con newlines -> \\x01)
        local method = "GET"
        local body = ""
        local hs = {}
        if R.type(opts) == "table" then
                if R.type(opts.Method) == "string" then method = opts.Method end
                if R.type(opts.Body) == "string" then body = opts.Body end
                if R.type(opts.Headers) == "table" then
                        for hk, hv in R.pairs(opts.Headers) do
                                R.insert(hs, R.tostring(hk) .. ": " .. R.tostring(hv))
                        end
                end
        end
        R.print("\\0MITM " .. n .. " " .. label .. " " .. url)
        if method ~= "GET" or body ~= "" or #hs > 0 then
                R.print("\\0MITMOPT " .. n .. " " .. method)
                R.print("\\0MITMHDR " .. n .. " " .. R.concat(hs, "\\r\\n"))
                R.print("\\0MITMBODY " .. n .. " " .. R.gsub(body, "\\n", "\\x01"))
        end
        R.print(__PAD)
        -- espera la respuesta del driver (require de mitm/resp_N.luau)
        -- Formato del modulo: {__body, __code, __headers} (los headers REALES)
        -- OJO: el require del CLI devuelve MENSAJES DE ERROR como resultado
        -- string (pcall ok=true) - rechazarlos (contienen "resp_N.luau:")
        local deadline = R.clock() + 240
        while R.clock() < deadline do
                local ok, r = pcall(function() return require("./resp_" .. n) end)
                if ok and R.type(r) == "table" and R.type(r.__body) == "string" and #r.__body > 0 then
                        R.print("\\0MITMDONE " .. n .. " " .. #r.__body)
                        R.print(__PAD)
                        return { body = r.__body, code = r.__code or 200, headers = r.__headers or {} }
                end
        end
        R.print("\\0MITMTIMEOUT " .. n)
        R.print(__PAD)
        return nil
end
'''
anchor = "local function httpMatch(url)"
idx = base.find(anchor)
assert idx > 0, "ancla httpMatch no encontrada"
base = base[:idx] + mitm_fn + base[idx:]

# 4c) httpRequest fallback -> MITM
old = 'return callP(label .. "(" .. fmt(opts) .. ")", "response", "table")'
new = ('local __mb = __MITM(label, opts and opts.Url, opts)\n'
       '\t\t\tif __mb ~= nil then return { Body = __mb, StatusCode = 200, Success = true, Headers = {} } end\n'
       '\t\t\treturn callP(label .. "(" .. fmt(opts) .. ")", "response", "table")')
assert base.count(old) == 1, f"httpRequest fallback: {base.count(old)}"
base = base.replace(old, new)

# 4d) namecall HttpGet fallback -> MITM
old = 'return callP(calleeText .. "(" .. fmtArgs(R.unpack(args, 1, args.n)) .. ")", "response", "string")'
new = ('local __mb = __MITM(name, R.type(a1) == "string" and a1 or nil, R.type(a1) == "table" and a1 or nil)\n'
       '\t\t\tif __mb ~= nil then\n'
       '\t\t\t\tif R.type(a1) == "table" and (name == "RequestAsync" or name == "PostAsync") then\n'
       '\t\t\t\t\treturn { Body = __mb.body, StatusCode = __mb.code, Success = __mb.code == 200, Headers = __mb.headers }\n'
       '\t\t\t\tend\n'
       '\t\t\t\treturn __mb.body\n'
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

# 4g) isfile: SOLO el cache del bootstrapper existe; el json de sesion NO
#     (replica el estado v1 del device: primera corrida sin ningun json).
#     OJO: isfile(json)=true + readfile(json)=nil = estado corrupto que el
#     device nunca tiene y diverge el flujo del VM.
old = 'E.isfile = function(p) comment("isfile(" .. fmt(p) .. ") -> false"); return false end'
new = ('E.isfile = function(p)\n'
       '\tif R.type(p) == "string" and p:find(__BOOTPATH, 1, true) then\n'
       '\t\tcomment("isfile(" .. fmt(p) .. ") -> true")\n'
       '\t\treturn true\n'
       '\tend\n'
       '\tcomment("isfile(" .. fmt(p) .. ") -> false"); return false\n'
       'end')
if base.count(old) == 1:
    base = base.replace(old, new)
    print("    isfile parcheado (solo bootstrapper)")

# 4h) entorno Delta fiel: syn = TABLA (Synapse compat), delfolder = funcion,
#     ldrupd8m = nil (el stub solo lo setea en el path de descarga CDN; con
#     cache -como en el cel del user- es nil). El envlog fabricaba proxies
#     truthy para esos nombres y el VM moria en State294.
old = 'E.http = { request = httpRequest("http.request") }'
new = ('E.http = { request = httpRequest("http.request") }\n'
       '-- DELTA-CAMO: syn es una tabla real (Synapse-X compat), delfolder existe\n'
       'E.delfolder = function(p) emit({ text = "delfolder(" .. fmt(p) .. ")" }) end\n'
       'E.syn = {\n'
       '\trequest = E.request,\n'
       '\thttp_request = E.http_request,\n'
       '\twritefile = E.writefile,\n'
       '\treadfile = E.readfile,\n'
       '\tisfile = E.isfile,\n'
       '\tisfolder = E.isfolder,\n'
       '\tappendfile = E.appendfile,\n'
       '\tlistfiles = E.listfiles,\n'
       '\tdelfile = E.delfile,\n'
       '\tdelfolder = E.delfolder,\n'
       '\tmakefolder = E.makefolder,\n'
       '\tqueue_on_teleport = E.queue_on_teleport,\n'
       '\tqueueonteleport = E.queueonteleport,\n'
       '\tsetclipboard = E.setclipboard,\n'
       '\ttoclipboard = E.toclipboard,\n'
       '\tgetgenv = E.getgenv,\n'
       '\tgetexecutorname = E.getexecutorname,\n'
       '\tidentifyexecutor = E.identifyexecutor,\n'
       '\tfireclickdetector = E.fireclickdetector,\n'
       '\tprotect_gui = function(gui) return gui end,\n'
       '}\n'
       'E.fireserver = function(...) emit({ text = "fireserver(" .. fmtArgs(...) .. ")" }) end')
assert base.count(old) == 1, f"syn-table: {base.count(old)}"
base = base.replace(old, new)
print("    syn (tabla) + delfolder + fireserver agregados")

# 4i) ldrupd8m debe leerse nil (path cache), no un proxy truthy
old = '''        __index = function(_, k)
                if DEVIRT_CAPTURE[k] ~= nil then return DEVIRT_CAPTURE[k] end'''
new = '''        __index = function(_, k)
                if k == "ldrupd8m" then return nil end
                if DEVIRT_CAPTURE[k] ~= nil then return DEVIRT_CAPTURE[k] end'''
assert base.count(old) == 1, f"ldrupd8m-nil: {base.count(old)}"
base = base.replace(old, new)
print("    ldrupd8m -> nil (path cache)")

# 4j) JSONDecode/JSONEncode REALES: los responses de x.luarmor.net son JSON
#     arrays (["hex1","hex2",...]) que el VM parsea con HttpService:JSONDecode;
#     el generico de envlog devuelve un proxy y la cadena moria.
json_code = '''
-- ================== JSON real (patch MITM) ==================
-- IIFE: solo 1 local top-level (el chunk de envlog esta al limite de 200)
local __JSON = (function()
local function __jsonSkip(s, i)
        while i <= #s do
                local c = s:sub(i, i)
                if c == " " or c == "\\t" or c == "\\n" or c == "\\r" then i += 1 else break end
        end
        return i
end
local function __jsonVal(s, i)
        i = __jsonSkip(s, i)
        local c = s:sub(i, i)
        if c == "[" then
                local t = {}
                i = __jsonSkip(s, i + 1)
                if s:sub(i, i) == "]" then return t, i + 1 end
                while true do
                        local v
                        v, i = __jsonVal(s, i)
                        t[#t + 1] = v
                        i = __jsonSkip(s, i)
                        local d = s:sub(i, i)
                        if d == "," then i += 1
                        elseif d == "]" then return t, i + 1
                        else R.error("json: expected , or ] at " .. i, 0) end
                end
        elseif c == "{" then
                local t = {}
                i = __jsonSkip(s, i + 1)
                if s:sub(i, i) == "}" then return t, i + 1 end
                while true do
                        i = __jsonSkip(s, i)
                        local k
                        k, i = __jsonVal(s, i)
                        i = __jsonSkip(s, i)
                        if s:sub(i, i) ~= ":" then R.error("json: expected : at " .. i, 0) end
                        i = __jsonSkip(s, i + 1)
                        local v
                        v, i = __jsonVal(s, i)
                        t[k] = v
                        i = __jsonSkip(s, i)
                        local d = s:sub(i, i)
                        if d == "," then i += 1
                        elseif d == "}" then return t, i + 1
                        else R.error("json: expected , or } at " .. i, 0) end
                end
        elseif c == '"' then
                i += 1
                local out, buf = {}, {}
                local function flush() out[#out + 1] = R.concat(buf); buf = {} end
                while true do
                        local ch = s:sub(i, i)
                        if ch == "" then R.error("json: unterminated string", 0) end
                        if ch == '"' then i += 1; flush(); return R.concat(out), i end
                        if ch == "\\\\" then
                                local n = s:sub(i + 1, i + 1)
                                if n == "n" then buf[#buf + 1] = "\\n"; i += 2
                                elseif n == "t" then buf[#buf + 1] = "\\t"; i += 2
                                elseif n == "r" then buf[#buf + 1] = "\\r"; i += 2
                                elseif n == "b" then buf[#buf + 1] = "\\8"; i += 2
                                elseif n == "f" then buf[#buf + 1] = "\\12"; i += 2
                                elseif n == "u" then
                                        local cp = R.tonumber(s:sub(i + 2, i + 5), 16)
                                        if cp then
                                                if cp < 0x80 then buf[#buf + 1] = R.char(cp)
                                                elseif cp < 0x800 then buf[#buf + 1] = R.char(0xC0 + (cp // 64), 0x80 + (cp % 64))
                                                else buf[#buf + 1] = R.char(0xE0 + (cp // 4096), 0x80 + ((cp // 64) % 64), 0x80 + (cp % 64)) end
                                                i += 6
                                        else
                                                buf[#buf + 1] = n; i += 2
                                        end
                                else buf[#buf + 1] = n; i += 2 end
                        else
                                buf[#buf + 1] = ch; i += 1
                        end
                        if #buf >= 256 then flush() end
                end
        elseif s:sub(i, i + 3) == "true" then return true, i + 4
        elseif s:sub(i, i + 4) == "false" then return false, i + 5
        elseif s:sub(i, i + 3) == "null" then return nil, i + 4
        else
                local j = i
                while i <= #s and R.find("[-+.eE0123456789]", s:sub(i, i), 1) do i += 1 end
                if i == j then R.error("json: unexpected char at " .. i, 0) end
                return R.tonumber(s:sub(j, i - 1)), i
        end
end
local function __jsonDec(s)
        local v = __jsonVal(s, 1)
        return v
end
local function __jsonEnc(v)
        local t = R.type(v)
        if t == "nil" then return "null"
        elseif t == "boolean" then return R.tostring(v)
        elseif t == "number" then
                if v == v // 1 and R.abs(v) < 1e15 then return R.fmt("%d", v) end
                return R.fmt("%.14g", v)
        elseif t == "string" then
                local out = R.gsub(v, '[%c"\\\\]', function(c)
                        local b = R.byte(c)
                        if c == '"' then return '\\\\"'
                        elseif c == "\\\\" then return "\\\\\\\\"
                        elseif c == "\\n" then return "\\\\n"
                        elseif c == "\\t" then return "\\\\t"
                        elseif c == "\\r" then return "\\\\r" end
                        return R.fmt("\\\\u%04x", b)
                end)
                return '"' .. out .. '"'
        elseif t == "table" then
                local isArr = (#v > 0) or (R.next(v) == nil)
                local parts = {}
                if isArr then
                        for x = 1, #v do parts[x] = __jsonEnc(v[x]) end
                        return "[" .. R.concat(parts, ",") .. "]"
                end
                for k, x in R.pairs(v) do
                        parts[#parts + 1] = __jsonEnc(R.tostring(k)) .. ":" .. __jsonEnc(x)
                end
                return "{" .. R.concat(parts, ",") .. "}"
        end
        return "null"
end
return { dec = __jsonDec, enc = __jsonEnc }
end)()
-- fin JSON patch
'''
anchor = "local R = {\n"
idx = base.find(anchor)
assert idx > 0, "marcador R no encontrado para JSON"
# insertar DESPUES de la tabla R (busco el cierre "}\n" siguiente linea local)
close_marker = "\nlocal START = R.clock()\n"
idx2 = base.find(close_marker)
assert idx2 > 0, "marcador START no encontrado"
base = base[:idx2] + json_code + base[idx2:]
print("    JSON decoder/encoder real inyectado")

# 4l) INSTRUMENTACION: el VM accede tablas RAW (sin trace). Loguear cada
#     field-read del response table y del JSON decodificado para ver cual es nil.
old = ('local __mb = __MITM(label, opts and opts.Url, opts)\n'
       '\t\t\tif __mb ~= nil then return { Body = __mb, StatusCode = 200, Success = true, Headers = {} } end\n'
       '\t\t\treturn callP(label .. "(" .. fmt(opts) .. ")", "response", "table")')
new = ('local __mb = __MITM(label, opts and opts.Url, opts)\n'
       '\t\t\tif __mb ~= nil then\n'
       '\t\t\t\tlocal __resp = {}\n'
       '\t\t\t\tR.rawset(__resp, "Body", __mb.body)\n'
       '\t\t\t\tR.rawset(__resp, "StatusCode", __mb.code)\n'
       '\t\t\t\tR.rawset(__resp, "Success", __mb.code == 200)\n'
       '\t\t\t\tR.rawset(__resp, "Headers", __mb.headers)\n'
       '\t\t\t\tR.rawset(__resp, "StatusMessage", "OK")\n'
       '\t\t\t\tR.setmetatable(__resp, { __index = function(_, k)\n'
       '\t\t\t\t\t\tR.print("\\0RESPTOUCH " .. R.tostring(k))\n'
       '\t\t\t\t\t\tR.print(__PAD)\n'
       '\t\t\t\t\t\treturn nil\n'
       '\t\t\t\t\tend })\n'

       '\t\t\t\treturn __resp\n'
       '\t\t\tend\n'
       '\t\t\treturn callP(label .. "(" .. fmt(opts) .. ")", "response", "table")')
assert base.count(old) == 1, f"resp-instrument: {base.count(old)}"
base = base.replace(old, new)
print("    response table instrumentado (RESPTOUCH)")

old = '''        -- --cfg falsy=a,b: calls of these names return false (explore other branches)'''
new = '''        -- JSON real (patch MITM): HttpService:JSONDecode/JSONEncode
        -- OJO: los VM Luraph usan RAWGET en las tablas (by-pass de metamethods,
        -- documentado en envlog para v14.5) -> los datos deben estar RAW en la
        -- tabla, no detras de __index. La instrumentacion queda para los MISSES.
        if name == "JSONDecode" and R.type(a1) == "string" then
                emit({ text = calleeText .. "(" .. fmtArgs(R.unpack(args, 1, args.n)) .. ")" })
                local __dec = __JSON.dec(a1)
                if R.type(__dec) == "table" then
                        local __jt = {}
                        for i = 1, #__dec do R.rawset(__jt, i, __dec[i]) end
                        for k, v in R.pairs(__dec) do
                                if R.type(k) ~= "number" then R.rawset(__jt, k, v) end
                        end
                        R.setmetatable(__jt, {
                                __index = function(_, k)
                                        local v = __dec[k]
                                        R.print("\\0JSONTOUCH-MISS " .. R.tostring(k))
                                        R.print(__PAD)
                                        return v
                                end,
                                __len = function() return #__dec end,
                        })
                        return __jt
                end
                return __dec
        end
        if name == "JSONEncode" and R.type(a1) ~= nil then
                emit({ text = calleeText .. "(" .. fmtArgs(R.unpack(args, 1, args.n)) .. ")" })
                return __JSON.enc(a1)
        end
        -- --cfg falsy=a,b: calls of these names return false (explore other branches)'''
assert base.count(old) == 1, f"json-hook: {base.count(old)}"
base = base.replace(old, new)
print("    hook JSONDecode/JSONEncode (raw-populated + miss-log) en onCall")

# 4m) DIAGNOSTICO tostring: loguear el VALOR (truncado) para ver que procesa el VM
old = '''E.tostring = function(...)
        local v = ...
        if CFG.ptrace then R.print("[tostring]", isP(v) and (INFO[v].name or INFO[v].hint) or R.typeof(v)) end'''
new = '''E.tostring = function(...)
        local v = ...
        if CFG.ptrace then R.print("[tostring]", isP(v) and (INFO[v].name or INFO[v].hint) or R.typeof(v)) end
        if CFG.ptrace and R.type(v) == "string" and #v < 200 then
                R.print("\\0TOSTR " .. R.tostring(R.sub(v, 1, 80)))
                R.print(__PAD)
        end'''
assert base.count(old) == 1, f"tostr: {base.count(old)}"
base = base.replace(old, new)
print("    tostring diagnostico (TOSTR) agregado")
old = '''                                return f(...)
                        end
                else'''
new = '''                                if k == "sub" and CFG.ptrace and R.select("#", ...) > 0 and R.type((...)) == "string" and #(...) < 200 then
                                        local __s = (...)
                                        R.print("\\0SUB " .. R.tostring(R.sub(__s, 1, 24)) .. " [" .. R.tostring(R.select(2, ...)) .. "," .. R.tostring(R.select(3, ...)) .. "]")
                                end
                                if k == "sub" and R.select("#", ...) > 0 and (...) == nil then
                                        local __a2 = R.select(2, ...)
                                        local __a3 = R.select(3, ...)
                                        R.print("\\0SUBNIL sub(nil, " .. R.tostring(__a2) .. ", " .. R.tostring(__a3) .. ")")
                                        R.print(__PAD)
                                        return nil
                                end
                                return f(...)
                        end
                else'''
assert base.count(old) == 1, f"subnil: {base.count(old)}"
base = base.replace(old, new)
print("    string.sub logging (SUB/SUBNIL) agregado")

# 4n) SWAP del cache P2D para el LOADER: el chunk del loader (~980KB) hace su
#     propia sonda Path2D con params que COLISIONAN con el bootstrapper
#     (|0.75, |0.5, |0.4-arc) pero valores distintos. Al cargar el loader,
#     __P2D se cambia por E.__L2D (inyectado por el prelude desde apply_p2d2).
old = '''        local f, err = R.loadstring(patched or src, chunkname)
        if not f then return nil, err end
        R.setfenv(f, ENV)
        comment("loadstring() of " .. #src .. " bytes: " .. quote(R.sub(src, 1, 200)))
        return f
end'''
new = '''        local f, err = R.loadstring(patched or src, chunkname)
        if not f then return nil, err end
        R.setfenv(f, ENV)
        comment("loadstring() of " .. #src .. " bytes: " .. quote(R.sub(src, 1, 200)))
        -- MITM: el chunk del LOADER hace su PROPIA sonda Path2D
        -- (robusto para tamano desconocido: cualquier fuente grande que NO
        -- sea el bootstrapper universal = el loader de este script)
        if R.type(src) == "string" and #src > 200000 and not R.find(src, "Luarmor V4 bootstrapper", 1, true) and not R.rawget(E, "__L2DUSED") then
                local __l2d = R.rawget(E, "__L2D")
                if __l2d then
                        __P2D = __l2d
                        R.rawset(E, "__L2DUSED", true)
                        R.print("\\0L2DSWAP loader P2D cache activado")
                        R.print(__PAD)
                end
        end
        return f
end'''
assert base.count(old) == 1, f"l2d-swap: {base.count(old)}"
base = base.replace(old, new)
print("    swap del cache P2D del loader (L2DSWAP) parcheado")

out = MITM_DIR + "/mitm_harness.luau"
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
