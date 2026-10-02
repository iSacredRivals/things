#!/usr/bin/env python3
"""Replay del WHITELIST LOADER de Luarmor (obf_5, 980 KB) a velocidad nativa.

Objetivo: ver que hace el loader DESPUES del status check (donde murio la
cadena del usuario) y capturar la URL del fetch premium. Env:
  - magic instances (propiedades encadenables, GetChildren -> {})
  - spawn por coroutine (watchdogs aparcan en el primer yield)
  - wait yield-aware
  - HttpService con JSONDecode real + router de respuestas
  - script_key del usuario instalado
"""
import os
import re
import subprocess

BASE = "aurora_qo"
EXTR = os.path.join(BASE, "extracted")
WS = os.path.join(BASE, "workspace_zip")
OUT = os.path.join(BASE, "analysis", "replay")
LUAU = "deobf/bin/luau"
os.makedirs(OUT, exist_ok=True)

KEY = "LbdcJNWbjhlelJHknRFNRcbBzibDAyTl"
CAPTURE_TIME = 1790732017


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


resp = {}
for n in ("04", "05", "06", "07", "09"):
    pat = next(p for p in os.listdir(WS)
               if p.startswith(f"qodump_1790732004_{n}_") and not p.endswith(".meta"))
    resp[n] = rd(os.path.join(WS, pat))

loader = rd(os.path.join(EXTR, "obf_5.lua"))
# los dispatch loops del VM del loader tambien instrumentados
n_loops = loader.count("while true do ")
loader_instr = loader.replace(
    "while true do ",
    "while true do __VMC+=1;if __VMC%100000000==0 then print('[VM] '..__VMC..' steps') end; ")
loader_instr = "local __VMC=0\n" + loader_instr

sync_body = '{"nodes":["https://sdkapi-public.luarmor.net/"],"st":%d}' % CAPTURE_TIME
check_key_body = ('{"success":true,"message":"Key authorized","key":{"key":"%s","status":"active"'
                  ',"expiration":1799999999},"scriptData":{},"script":{"id":"0ae9fe4cf963e3a13d25'
                  'eed0e2ce5940","name":"bloxfruits","version":"0056"}}') % KEY

HOOK = r"""
-- ================= REPLAY whitelist loader (obf_5) =================
local real_loadstring = loadstring
local captured = 0
local nreq = 0
local waitn = 0

local print_budget = 3000
local real_print = print
local function budget_print(...)
        if print_budget > 0 then
                print_budget = print_budget - 1
                local n = select("#", ...)
                local parts = {}
                for i = 1, n do parts[i] = tostring(select(i, ...)) end
                real_print(table.concat(parts, "\t"))
        elseif print_budget == 0 then
                print_budget = -1
                real_print("[...] print budget agotado")
        end
end
print = budget_print
warn = budget_print or budget_print

-- ---------- JSON real ----------
local function json_parse(s)
        local i = 1
        local function skip()
                while i <= #s and (string.sub(s, i, i):find("[ \t\r\n]")) do i = i + 1 end
        end
        local function val()
                skip()
                local c = string.sub(s, i, i)
                if c == "{" then
                        i = i + 1
                        local t = {}
                        skip()
                        if string.sub(s, i, i) == "}" then i = i + 1; return t end
                        while true do
                                skip()
                                local k = val()
                                skip()
                                if string.sub(s, i, i) ~= ":" then error("json :") end
                                i = i + 1
                                local v = val()
                                t[k] = v
                                skip()
                                local d = string.sub(s, i, i)
                                if d == "," then i = i + 1
                                elseif d == "}" then i = i + 1; return t
                                else error("json obj end") end
                        end
                elseif c == "[" then
                        i = i + 1
                        local a = {}
                        skip()
                        if string.sub(s, i, i) == "]" then i = i + 1; return a end
                        local n = 1
                        while true do
                                a[n] = val()
                                n = n + 1
                                skip()
                                local d = string.sub(s, i, i)
                                if d == "," then i = i + 1
                                elseif d == "]" then i = i + 1; return a
                                else error("json arr end") end
                        end
                elseif c == '"' then
                        i = i + 1
                        local out = {}
                        while true do
                                local ch = string.sub(s, i, i)
                                if ch == '"' then i = i + 1; return table.concat(out)
                                elseif ch == "\\" then
                                        local e = string.sub(s, i + 1, i + 1)
                                        i = i + 2
                                        if e == "n" then out[#out + 1] = "\n"
                                        elseif e == "t" then out[#out + 1] = "\t"
                                        elseif e == "r" then out[#out + 1] = "\r"
                                        elseif e == "u" then
                                                out[#out + 1] = string.char(tonumber(string.sub(s, i, i + 3), 16) % 256)
                                                i = i + 4
                                        else out[#out + 1] = e end
                                else
                                        out[#out + 1] = ch
                                        i = i + 1
                                end
                        end
                elseif string.sub(s, i, i + 3) == "true" then i = i + 4; return true
                elseif string.sub(s, i, i + 4) == "false" then i = i + 5; return false
                elseif string.sub(s, i, i + 3) == "null" then i = i + 4; return nil
                else
                        local j = string.find(s, "[%,%]%}]", i) or (#s + 1)
                        local num = tonumber(string.sub(s, i, j - 1))
                        if num == nil then error("json num @" .. i .. " " .. string.sub(s, i, i + 20)) end
                        i = j
                        return num
                end
        end
        skip()
        return val()
end

local function json_encode(v)
        local t = type(v)
        if t == "string" then
                return '"' .. (string.gsub(v, '[%c"\\]', function(c)
                        if c == '"' then return '\\"'
                        elseif c == "\\" then return "\\\\"
                        elseif c == "\n" then return "\\n"
                        elseif c == "\t" then return "\\t"
                        else return string.format("\\u%04x", string.byte(c)) end
                end)) .. '"'
        elseif t == "number" then return string.format("%.14g", v)
        elseif t == "boolean" then return tostring(v)
        elseif t == "table" then
                local parts = {}
                local isarr = (next(v) ~= nil) and (v[1] ~= nil or #v > 0)
                if isarr then
                        for k, x in ipairs(v) do parts[#parts + 1] = json_encode(x) end
                        return "[" .. table.concat(parts, ",") .. "]"
                end
                for k, x in pairs(v) do parts[#parts + 1] = json_encode(tostring(k)) .. ":" .. json_encode(x) end
                return "{" .. table.concat(parts, ",") .. "}"
        end
        return "null"
end

-- ---------- wait/spawn por coroutine ----------
local function wait_stub(n)
        local co, ismain = coroutine.running()
        if not ismain and co then
                return coroutine.yield(n or 0.03)
        end
        waitn = waitn + 1
        if waitn > 20000 then error("WAIT-FLOOD main-thread: " .. waitn, 0) end
        return n or 0.03
end

local function spawn_thread(f, ...)
        if type(f) ~= "function" then return end
        local co = coroutine.create(f)
        local ok, e = coroutine.resume(co, ...)
        if not ok then real_print("[SPAWN-ERR] " .. tostring(e):sub(1, 300)) end
        return co
end

-- ---------- magic instances ----------
local function magic(parent_hint)
        local t
        t = setmetatable({ ClassName = "Instance" }, {
                __call = function(_, ...) return t end,
                __index = function(_, k)
                        if k == "Wait" or k == "wait" then return function() return wait_stub() end end
                        if k == "GetChildren" or k == "GetDescendants" or k == "GetPlayers"
                                or k == "listfiles" then
                                return function() return {} end
                        end
                        if k == "GetPlayers" then return function() return {} end end
                        if k == "Connect" or k == "Once" or k == "connect" then
                                return function() return { Disconnect = function() end, Connected = true } end
                        end
                        if k == "FindFirstChild" or k == "FindFirstChildOfClass"
                                or k == "WaitForChild" then
                                return function() return nil end
                        end
                        if k == "FindFirstChildWhichIsA" or k == "FindFirstAncestorOfClass" then
                                return function() return nil end
                        end
                        if k == "GetService" then
                                return function(_, name)
                                        if name == "HttpService" then return HTTP_SERVICE end
                                        return magic("Service:" .. tostring(name))
                                end
                        end
                        if k == "LocalPlayer" then return localplayer_stub end
                        if k == "Parent" then return parent_hint end
                        if k == "Name" then return "Instance" end
                        return magic(t)
                end,
                __newindex = function() end,
                __tostring = function() return "Instance" end,
        })
        return t
end

local localplayer_stub = setmetatable({ Name = "Player", UserId = 123456789,
        DisplayName = "Player" }, {
        __index = function(_, k)
                if k == "Wait" or k == "wait" then return function() return wait_stub() end end
                if k == "GetChildren" then return function() return {} end end
                return function() end
        end,
        __tostring = function() return "Player" end,
})

-- ---------- router HTTP ----------
local RESP = {__RESPS__}
local STATUS = __STATUS__
local SYNC = __SYNC__
local CHECKKEY = __CHECKKEY__

local function router(url)
        if type(url) ~= "string" then return nil end
        if string.find(url, "x.luarmor.net", 1, true) then
                nreq = nreq + 1
                real_print("[HTTP] x.luarmor.net #" .. nreq)
                return RESP[nreq]
        end
        if string.find(url, "roblox-auth.luarmor.net/status", 1, true) then
                real_print("[HTTP] status -> grabada")
                return STATUS
        end
        if string.find(url, "roblox-auth.luarmor.net", 1, true) then
                real_print("[HTTP] roblox-auth no-status: " .. string.sub(url, 1, 200))
                return CHECKKEY
        end
        if string.find(url, "sdkapi-public.luarmor.net/sync", 1, true) then
                real_print("[HTTP] sync -> mock")
                return SYNC
        end
        if string.find(url, "check_key", 1, true) then
                real_print("[HTTP] check_key -> mock: " .. string.sub(url, 1, 200))
                return CHECKKEY
        end
        real_print("[HTTP] ??? NO-MOCKEADA: " .. string.sub(url, 1, 250))
        return nil
end

local function http_call(t)
        local url = type(t) == "table" and t.Url or t
        local body = router(url)
        if body == nil then return { Body = "{}", StatusCode = 200, Success = true, Headers = {} } end
        return { Body = body, StatusCode = 200, Success = true, Headers = {} }
end

local HTTP_SERVICE
HTTP_SERVICE = setmetatable({ ClassName = "HttpService" }, {
        __index = function(_, k)
                if k == "GetAsync" or k == "RequestAsync" then
                        return function(_, url) return router(url) or "{}" end
                end
                if k == "JSONDecode" then return function(_, s) return json_parse(s) end end
                if k == "JSONEncode" then return function(_, v) return json_encode(v) end end
                if k == "GenerateGUID" then return function() return "0f0f0f0f-1111-2222-3333-444455556666" end end
                if k == "HttpEnabled" then return true end
                if k == "HttpCacheHttpEnabled" or k == "HttpUseCachedResponse" then return true end
                return function() end
        end,
        __tostring = function() return "HttpService" end,
})

-- ---------- loadstring hook ----------
local function hook_loadstring(source, chunkname)
        captured = captured + 1
        real_print("\n==LS" .. captured .. "== cn=" .. tostring(chunkname) ..
                " len=" .. (source and #source or -1))
        if type(source) == "string" and #source >= 3000 then
                real_print("==LSB" .. captured .. "==")
                real_print(source)
                real_print("==LSE" .. captured .. "==")
        end
        if type(source) ~= "string" then return real_loadstring(source, chunkname) end
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

-- ---------- game ----------
local game
game = setmetatable({ ClassName = "DataModel" }, {
        __index = function(_, k)
                if k == "GetService" then
                        return function(_, name)
                                if name == "HttpService" then return HTTP_SERVICE end
                                return magic("Service:" .. tostring(name))
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
                if k == "LocalPlayer" then return localplayer_stub end
                if k == "CoreGui" then
                        -- consola VACIA: el anti-tamper no encuentra nada
                        return magic("CoreGui")
                end
                if k == "Loaded" then return true end
                if k == "IsLoaded" then return function() return true end end
                return magic("game." .. tostring(k))
        end,
        __tostring = function() return "DataModel" end,
})

-- ---------- genv ----------
local genv = getfenv()
genv._ENV = genv
genv.game = game
genv.workspace = magic("Workspace")
genv.loadstring = hook_loadstring
genv.script_key = __KEY__
genv.genv = genv
genv.print = budget_print
genv.warn = budget_print
genv.spawn = spawn_thread
genv.delay = function(_, f) spawn_thread(f) end
genv.defer = function(f) spawn_thread(f) end
genv.wait = wait_stub
genv.tick = function() return os.time() + os.clock() end
genv.time = function() return os.time() end
local os2 = setmetatable({}, { __index = os })
os2.time = os.time
os2.date = os.date
os2.clock = os.clock
genv.os = os2
local task_stub = setmetatable({}, { __index = function(_, k)
        if k == "clock" then return os.clock end
        if k == "spawn" or k == "defer" then return spawn_thread end
        if k == "delay" then return function(_, f) spawn_thread(f) end end
        if k == "wait" then return wait_stub end
        return function() end
end })
genv.task = task_stub
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
genv.shared = {}
genv.setclipboard = function() end
genv.firetouchinterest = function() end
genv.queue_on_teleport = function() end
genv.hookfunction = function(f) return f end
genv.hookmetamethod = function() return function() end end
genv.getconnections = function() return {} end
genv.getcallingscript = function() return nil end
genv.checkcaller = function() return false end
genv.setfpscap = function() end
genv.getinstances = function() return {} end
genv.getnilinstances = function() return {} end
genv.UserSettings = function() return magic("UserSettings") end
genv.settings = function() return magic("settings") end
genv.gethui = function() return magic("hui") end
genv.cloneref = function(x) return x end
genv.compareinstances = function(a, b) return a == b end
genv.FireServer = nil
genv.Instance = setmetatable({}, { __index = function() return function()
        return magic("new") end end })
genv.Enum = setmetatable({}, { __index = function() return setmetatable({}, {
        __index = function() return function() end end }) end })
-- datatypes reales de la suite
local __DT = (function()
__DATATYPES__
end)()
genv.UDim = __DT.UDim
genv.UDim2 = __DT.UDim2
genv.CFrame = __DT.CFrame
genv.Color3 = __DT.Color3
genv.Vector2 = __DT.Vector2
genv.Rect = __DT.Rect
genv.Ray = __DT.Ray
genv.NumberRange = __DT.NumberRange
genv.Path2DControlPoint = __DT.Path2DControlPoint
genv.Vector3int16 = __DT.Vector3int16
genv.Vector2int16 = __DT.Vector2int16
genv.NumberSequence = __DT.NumberSequence
genv.ColorSequence = __DT.ColorSequence
genv.NumberSequenceKeypoint = __DT.NumberSequenceKeypoint
genv.ColorSequenceKeypoint = __DT.ColorSequenceKeypoint
genv.Vector3 = setmetatable({ new = function(x, y, z) return { X = x or 0, Y = y or 0, Z = z or 0 } end },
        { __index = function() return function() return {} end end })
genv.DateTime = setmetatable({}, { __index = function(_, k)
        if k == "now" or k == "fromUnixTimestamp" then
                return function() return { UnixTimestamp = os.time(), UnixTimestampMillis = os.time() * 1000 } end
        end
        return function() return {} end
end })
genv.Faces = setmetatable({}, { __index = function() return function() return setmetatable({}, {
        __index = function() return true end }) end end })
genv.Axes = genv.Faces
genv.PhysicalProperties = setmetatable({}, { __index = function() return function() return {} end end })
genv.Region3 = setmetatable({}, { __index = function() return function() return {} end end })
genv.TweenInfo = setmetatable({}, { __index = function() return function() return {} end end })
genv.Random = setmetatable({}, { __index = function(_, k)
        if k == "new" then return function() return {
                NextNumber = function() return 0.5 end,
                NextInteger = function() return 1 end,
        } end end end })

local fn, err = real_loadstring(__TARGET__)
assert(fn, "compile error loader: " .. tostring(err))
real_print("[WRAP] loader compilado, ejecutando...")

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
                real_print("[SET] " .. tostring(k) .. " = " .. type(v))
                genv[k] = v
        end,
})
setfenv(fn, proxy)
local ok, rerr = xpcall(fn, function(e)
        return tostring(e) .. "\n" .. debug.traceback(nil, 2)
end)
real_print("\n==RUN== ok=" .. tostring(ok) .. " err=" .. tostring(rerr):sub(1, 3000)
        .. " loadstrings=" .. captured .. " xreq=" .. nreq .. " waits=" .. waitn)
"""

hook = (HOOK
        .replace("__RESPS__", ", ".join(ls(resp[n]) for n in ("04", "05", "06", "07")))
        .replace("__STATUS__", ls(resp["09"]))
        .replace("__SYNC__", ls(sync_body))
        .replace("__CHECKKEY__", ls(check_key_body))
        .replace("__KEY__", '"%s"' % KEY)
        .replace("__CT__", str(CAPTURE_TIME)))

with open("deobf/datatypes.luau", encoding="utf-8") as f:
    dt_src = f.read().replace("--!nocheck", "", 1)
hook = hook.replace("__DATATYPES__", dt_src)

wrapped = "local __TARGET__ = " + ls(loader_instr) + "\n" + hook
wpath = os.path.join(OUT, "loader_wrap.luau")
with open(wpath, "w", encoding="latin-1") as f:
    f.write(wrapped)
print(f"[*] wrapper: {wpath} ({len(wrapped)} B) | loops instrumentados: {n_loops}")

print("[*] corriendo loader (timeout 150s SIGTERM)...")
try:
    r = subprocess.run(
        ["bash", "-c", f"timeout -s TERM 3600 '{LUAU}' '{wpath}'"],
        capture_output=True, timeout=3620)
    out = r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace")
except subprocess.TimeoutExpired as e:
    out = ((e.stdout or b"").decode("utf-8", "replace")
           + "\n!!!TIMEOUT\n" + (e.stderr or b"").decode("utf-8", "replace"))

rawp = os.path.join(OUT, "loader_raw.txt")
with open(rawp, "w", encoding="utf-8") as f:
    f.write(out)
print(f"[*] raw -> {rawp} ({len(out)} chars)")

print("\n========== RESUMEN ==========")
for pat, label in [
    (r"\[HTTP\][^\n]*", "HTTP"),
    (r"==LS\d+==[^\n]*", "LS"),
    (r"\[NILREAD\][^\n]*", "NILREAD"),
    (r"\[SET\][^\n]*", "SET"),
    (r"\[SPAWN-ERR\][^\n]*", "SPAWN-ERR"),
    (r"\[VM\][^\n]*", "VM"),
    (r"Luarmor[^\n]*", "BANNER"),
    (r"whitelist[^\n]*", "WHITELIST"),
]:
    lines = re.findall(pat, out)
    if lines:
        print(f"--- {label} ({len(lines)}):")
        for l in lines[:20]:
            print("   " + l[:170])
m = re.search(r"==RUN==(.*)", out, re.S)
if m:
    print("--- RUN:", m.group(1)[:3000])
else:
    print("--- sin ==RUN==. Cola:")
    print(out[-2000:])
