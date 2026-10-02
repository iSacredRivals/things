#!/usr/bin/env python3
"""Genera y corre un wrapper RAW-luau del bootstrapper V4 con REPLAY de las
respuestas reales de x.luarmor.net capturadas en el Delta del usuario.

Velocidad nativa (sin tracing de envlog). Captura toda fuente >= 3KB que pase
por loadstring con marcadores de stdout + guarda a disco si io existe.
"""
import os
import re
import subprocess
import sys

BASE = "aurora_qo"
WS = os.path.join(BASE, "workspace_zip")
EXTR = os.path.join(BASE, "extracted")
OUT = os.path.join(BASE, "analysis", "replay")
LUAU = "deobf/bin/luau"
os.makedirs(OUT, exist_ok=True)

KEY = "LbdcJNWbjhlelJHknRFNRcbBzibDAyTl"
CAPTURE_TIME = 1790732017  # timestamp de la sesion capturada


def rd(p):
    with open(p, encoding="latin-1") as f:
        return f.read()


def ls(s):
    lvl = 0
    while ("]" + "=" * lvl + "]") in s:
        lvl += 1
    if lvl == 0 and s.endswith("]"):
        lvl = 1
    eq = "=" * lvl
    return "[" + eq + "[\n" + s + "]" + eq + "]"


stub = rd(os.path.join(WS, "qodump_1790732004_01_api.luarmor.net_files_v4_loaders_0ae9fe4cf963e"))
bsdata = re.search(r"_bsdata0\s*=\s*(\{.*?\});", stub, re.S).group(1)

resp = {}
for n in ("04", "05", "06", "07", "09"):
    pat = next(p for p in os.listdir(WS)
               if p.startswith(f"qodump_1790732004_{n}_") and not p.endswith(".meta"))
    resp[n] = rd(os.path.join(WS, pat))

boot = rd(os.path.join(EXTR, "obf_4.lua"))
boot = boot.replace(":TK()(...)", ':TK()("f07dbcbe19a-sephal")', 1)

# instrumentar TODOS los dispatch loops con contador de steps (progreso visible)
n_loops = boot.count("while true do ")
boot_orig = boot
boot = "local __VMC=0\n" + boot.replace(
    "while true do ",
    "while true do __VMC+=1;if __VMC%25000000==0 then print('[VM] '..__VMC..' steps') end; ")
print(f"[*] loops instrumentados: {n_loops}")

sync_body = '{"nodes":["https://sdkapi-public.luarmor.net/"],"st":%d}' % CAPTURE_TIME
check_key_body = ('{"success":true,"message":"Key authorized","key":{"key":"%s","status":"active"'
                  ',"expiration":1799999999},"scriptData":{},"script":{"id":"0ae9fe4cf963e3a13d25'
                  'eed0e2ce5940","name":"bloxfruits","version":"0056"}}') % KEY

HOOK = r"""
-- ================= REPLAY Luarmor V4 (raw, velocidad nativa) =================
local real_loadstring = loadstring
local captured = 0
local RESP = {__RESPS__}
local STATUS = __STATUS__
local SYNC = __SYNC__
local CHECKKEY = __CHECKKEY__
local BOOT = __BOOT__
local nreq = 0
local waitn = 0

local print_budget = 3000
local real_print = print
real_print("[WRAP] iniciando wrapper")
local __LOGF = nil
pcall(function()
        __LOGF = io.open(__OUTDIR__ .. "/boot_live.log", "w")
end)
local function budget_print(...)
        if print_budget > 0 then
                print_budget = print_budget - 1
                local n = select("#", ...)
                local parts = {}
                for i = 1, n do parts[i] = tostring(select(i, ...)) end
                local line = table.concat(parts, "\t")
                real_print(line)
                if __LOGF then
                        pcall(function() __LOGF:write(line .. "\n") __LOGF:flush() end)
                end
        elseif print_budget == 0 then
                print_budget = -1
                real_print("[...] print budget agotado")
        end
end
print = budget_print
warn = budget_print

local function router(url)
        if type(url) ~= "string" then return nil end
        if string.find(url, "x.luarmor.net", 1, true) then
                nreq = nreq + 1
                real_print("[HTTP] x.luarmor.net #" .. nreq .. " (url " .. #url .. " B)")
                local b = RESP[nreq]
                if b then
                        real_print("[HTTP]    -> sirviendo " .. #b .. " B capturados")
                        return b
                end
                real_print("[HTTP]    !! sin respuesta capturada (nreq=" .. nreq .. ")")
                return nil
        end
        if string.find(url, "roblox-auth.luarmor.net/status", 1, true) then
                real_print("[HTTP] status -> grabada")
                return STATUS
        end
        if string.find(url, "roblox-auth.luarmor.net", 1, true) then
                real_print("[HTTP] roblox-auth (no-status) -> checkkey mock: " .. string.sub(url, 1, 160))
                return CHECKKEY
        end
        if string.find(url, "sdkapi-public.luarmor.net/sync", 1, true) then
                real_print("[HTTP] sync -> mock")
                return SYNC
        end
        if string.find(url, "check_key", 1, true) then
                real_print("[HTTP] check_key -> mock: " .. string.sub(url, 1, 160))
                return CHECKKEY
        end
        if string.find(url, "cdn.luarmor.net", 1, true) then
                real_print("[HTTP] cdn -> bootstrapper")
                return BOOT
        end
        real_print("[HTTP] ?? NO-MOCKEADA: " .. string.sub(url, 1, 200))
        return nil
end

local function http_call(t)
        local url = type(t) == "table" and t.Url or t
        local body = router(url)
        if body == nil then return { Body = "{}", StatusCode = 200, Success = true, Headers = {} } end
        return { Body = body, StatusCode = 200, Success = true, Headers = {} }
end

local function hook_loadstring(source, chunkname)
        captured = captured + 1
        real_print("\n==LS" .. captured .. "== cn=" .. tostring(chunkname) ..
                " len=" .. (source and #source or -1))
        if type(source) == "string" and #source >= 3000 then
                real_print("==LSB" .. captured .. "==")
                real_print(source)
                real_print("==LSE" .. captured .. "==")
                local okf, f = pcall(io.open, __OUTDIR__ .. "/ls" .. captured .. "_" .. #source .. ".lua", "w")
                if okf and f then
                        pcall(function() f:write(source) f:close() end)
                        real_print("[LS] guardado a disco")
                end
        end
        if type(source) ~= "string" then
                return real_loadstring(source, chunkname)
        end
        local real, err = real_loadstring(source, tostring(chunkname or "=cap" .. captured))
        if not real then
                real_print("[LS] COMPILE ERROR: " .. tostring(err))
                return nil, err
        end
        return function(...)
                setfenv(real, getfenv(2))
                return real(...)
        end, real
end

-- stub Roblox
local function stub_service(name)
        return setmetatable({ ClassName = name }, { __index = function() return function() end end })
end
local services = {}
local game = setmetatable({ ClassName = "DataModel" }, {
        __index = function(t, k)
                if k == "GetService" then
                        return function(_, name)
                                if not services[name] then services[name] = stub_service(name) end
                                return services[name]
                        end
                end
                if k == "HttpGet" or k == "HttpGetAsync" then
                        return function(_, url) return router(url) or "{}" end
                end
                if k == "HttpPost" or k == "HttpPostAsync" then
                        return function(_, url) return router(url) or "{}" end
                end
                if k == "PlaceId" then return 2753915549 end
                if k == "GameId" then return 994732206 end
                if k == "RobloxLocaleId" then return "en-us" end
                if k == "JobId" then return "0f0f0f0f-0f0f-0f0f-0f0f-0f0f0f0f0f0f" end
                if k == "CreatorId" then return 158323776 end
                if k == "CreatorType" then return "User" end
                if k == "Name" then return "Blox Fruits" end
                return function() end
        end,
})
local Players = stub_service("Players")
local localplayer_stub = setmetatable({ Name = "Player", UserId = 123456789,
        DisplayName = "Player", Character = stub_service("Model") }, {
        __index = function() return function() end end,
        __tostring = function() return "Player" end,
})

local genv = getfenv()
genv._ENV = genv
genv.game = game
genv.workspace = stub_service("Workspace")
genv.loadstring = hook_loadstring
genv.Players = Players
genv.print = budget_print
genv.warn = budget_print
genv._bsdata0 = __BSDATA__
genv.script_key = __KEY__
-- spawn/delay: ejecutan SINCRONO (con guard anti-flood en wait)
local depth = 0
local function syncspawn(f, ...)
        if depth > 16 then real_print("[SPAWN] profundidad maxima, descarto") return end
        depth = depth + 1
        local ok, e = pcall(f, ...)
        depth = depth - 1
        if not ok then real_print("[SPAWN] error: " .. tostring(e):sub(1, 200)) end
end
genv.spawn = syncspawn
genv.delay = function(_, f) syncspawn(f) end
genv.defer = function(f) syncspawn(f) end
local task_stub = setmetatable({}, { __index = function(_, k)
        if k == "clock" then return os.clock end
        if k == "spawn" or k == "defer" then return syncspawn end
        if k == "delay" then return function(_, f) syncspawn(f) end end
        return function() end
end })
genv.task = task_stub
local function wait_stub(n)
        waitn = waitn + 1
        if waitn > 2000 then error("WAIT-FLOOD: " .. waitn .. " waits (loop infinito)", 0) end
        return n or 0.03
end
genv.wait = wait_stub
genv.tick = function() return os.time() + os.clock() end
-- tiempo REAL: el congelado rompe esperas anti-instantaneo; la captura es fresca (1-2h)
genv.time = function() return os.time() end
local os2 = setmetatable({}, { __index = os, __metatable = os })
os2.time = os.time
os2.date = os.date
os2.clock = os.clock
genv.os = os2
genv.writefile = function(p, c)
        real_print("[WRITEFILE] " .. tostring(p) .. " (" .. (c and #c or 0) .. " B)")
end
genv.readfile = function(p) real_print("[READFILE] " .. tostring(p)) return "" end
genv.isfile = function() return false end
genv.isfolder = function() return false end
genv.makefolder = function() end
genv.listfiles = function() return {} end
genv.delfile = function() end
genv.identifyexecutor = function() return "Delta" end
genv.getexecutorname = function() return "Delta" end
genv.gethwid = function() return "d3b14c1f2a9b7e8c4d5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c" end
genv.getgenv = function() return genv end
genv.getrenv = function() return genv end
genv.http_request = http_call
genv.request = http_call
genv.http = { request = http_call }
genv.setclipboard = function() end
genv.shared = {}
genv.setclipboard = function() end
genv.firetouchinterest = function() end
genv.fireclickdetector = function() end
genv.queue_on_teleport = function() end
genv.hookfunction = function(f) return f end
genv.hookmetamethod = function() return function() end end
genv.getconnections = function() return {} end
genv.getcallingscript = function() return nil end
genv.getsenv = function() return genv end
genv.checkcaller = function() return false end
genv.setfpscap = function() end
genv.getinstances = function() return {} end
genv.getnilinstances = function() return {} end
genv.Instance = setmetatable({}, { __index = function() return function()
        return setmetatable({}, { __index = function() return function() end end })
end end })
genv.Enum = setmetatable({}, { __index = function() return setmetatable({}, {
        __index = function() return function() end end }) end })
-- datatypes reales de la suite (semillas identicas a Roblox Studio)
real_print("[WRAP] cargando datatypes...")
local __DT = (function()
__DATATYPES__
end)()
real_print("[WRAP] datatypes OK")
genv.UDim = __DT.UDim
genv.UDim2 = __DT.UDim2
genv.CFrame = __DT.CFrame
genv.Color3 = __DT.Color3
genv.Vector2 = __DT.Vector2
genv.Rect = __DT.Rect
genv.Ray = __DT.Ray
genv.NumberRange = __DT.NumberRange
genv.Vector3int16 = __DT.Vector3int16
genv.Vector2int16 = __DT.Vector2int16
genv.NumberSequenceKeypoint = __DT.NumberSequenceKeypoint
genv.ColorSequenceKeypoint = __DT.ColorSequenceKeypoint
genv.NumberSequence = __DT.NumberSequence
genv.ColorSequence = __DT.ColorSequence
genv.Path2DControlPoint = __DT.Path2DControlPoint
genv.Vector3 = setmetatable({ new = function(x, y, z) return { X = x or 0, Y = y or 0, Z = z or 0,
        Magnitude = 0, Dot = function() return 0 end } end },
        { __index = function() return function() return {} end end })
genv.DateTime = setmetatable({}, { __index = function(_, k)
        if k == "now" or k == "fromUnixTimestamp" or k == "fromUniversalTime" then
                return function() return { UnixTimestamp = __CT__, UnixTimestampMillis = __CT__ * 1000 } end
        end
        return function() return {} end
end })
genv.Faces = setmetatable({}, { __index = function() return function() return setmetatable({}, {
        __index = function() return true end }) end end })
genv.Axes = genv.Faces
genv.PhysicalProperties = setmetatable({}, { __index = function() return function() return {} end end })
genv.Region3 = setmetatable({}, { __index = function() return function() return {} end end })
genv.Region3int16 = genv.Region3
genv.TweenInfo = setmetatable({}, { __index = function() return function() return {} end end })
genv.Random = setmetatable({}, { __index = function(_, k)
        if k == "new" then return function() return {
                NextNumber = function() return 0.5 end,
                NextInteger = function() return 1 end,
        } end end end })
genv.Drawing = setmetatable({}, { __index = function() return function()
        return { Remove = function() end, Visible = true } end end })

local fn, err = real_loadstring(__TARGET__)
assert(fn, "compile error boot: " .. tostring(err))
real_print("[WRAP] boot compilado, ejecutando...")
-- el stub real deja ldrupd8m = fuente del bootstrapper antes de ejecutarlo
genv.ldrupd8m = __BOOT__  -- fuente ORIGINAL sin instrumentar

local nilreads = {}
local proxy = setmetatable({}, {
        __index = function(_, k)
                local v = genv[k]
                if v == nil then
                        if not nilreads[k] then
                                nilreads[k] = true
                                real_print("[NILREAD] " .. tostring(k))
                                real_print(debug.traceback("[stack " .. tostring(k) .. "]", 2))
                        end
                        return nil
                end
                return v
        end,
        __newindex = function(_, k, v)
                if k ~= nilreads then
                        real_print("[SET] " .. tostring(k) .. " = " .. type(v))
                end
                genv[k] = v
        end,
})
setfenv(fn, proxy)
local ok, rerr = xpcall(fn, function(e)
        return tostring(e) .. "\n" .. debug.traceback(nil, 2)
end)
real_print("\n==RUN== ok=" .. tostring(ok) .. " err=" .. tostring(rerr):sub(1, 2000)
        .. " loadstrings=" .. captured .. " xreq=" .. nreq .. " waits=" .. waitn)
"""

hook = (HOOK
        .replace("__RESPS__", ", ".join(ls(resp[n]) for n in ("04", "05", "06", "07")))
        .replace("__STATUS__", ls(resp["09"]))
        .replace("__SYNC__", ls(sync_body))
        .replace("__CHECKKEY__", ls(check_key_body))
        .replace("__BOOT__", ls(boot))
        .replace("__BSDATA__", bsdata)
        .replace("__KEY__", '"%s"' % KEY)
        .replace("__CT__", str(CAPTURE_TIME))
        .replace("__OUTDIR__", '"%s"' % OUT))

# datatypes reales de la suite (quitar --!nocheck, va dentro de un function)
with open("deobf/datatypes.luau", encoding="utf-8") as f:
    dt_src = f.read().replace("--!nocheck", "", 1)
hook = hook.replace("__DATATYPES__", dt_src)

wrapped = "local __TARGET__ = " + ls(boot) + "\n" + hook
wpath = os.path.join(OUT, "boot_wrap.luau")
with open(wpath, "w", encoding="latin-1") as f:
    f.write(wrapped)
print(f"[*] wrapper: {wpath} ({len(wrapped)} B)")

print("[*] corriendo (timeout 150s via SIGTERM, preserva stdout)...")
try:
    r = subprocess.run(
        ["bash", "-c", f"timeout -s TERM 900 '{LUAU}' '{wpath}'"],
        capture_output=True, timeout=920)
    out = r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace")
except subprocess.TimeoutExpired as e:
    out = ((e.stdout or b"").decode("utf-8", "replace")
           + "\n!!!TIMEOUT\n" + (e.stderr or b"").decode("utf-8", "replace"))

rawp = os.path.join(OUT, "boot_raw.txt")
with open(rawp, "w", encoding="utf-8") as f:
    f.write(out)
print(f"[*] raw -> {rawp} ({len(out)} chars)")

# resumen
print("\n========== RESUMEN ==========")
for pat, label in [
    (r"\[HTTP\][^\n]*", "HTTP"),
    (r"==LS\d+==[^\n]*", "LS"),
    (r"\[NILREAD\][^\n]*", "NILREAD"),
    (r"\[SET\][^\n]*", "SET"),
    (r"\[WRITEFILE\][^\n]*", "WRITEFILE"),
]:
    lines = re.findall(pat, out)
    print(f"--- {label} ({len(lines)}):")
    for l in lines[:25]:
        print("   " + l[:150])
m = re.search(r"==RUN==(.*)", out, re.S)
if m:
    print("--- RUN:", m.group(1)[:2000])
else:
    print("--- sin ==RUN== (colgo/timeout). Cola del output:")
    print(out[-1500:])
