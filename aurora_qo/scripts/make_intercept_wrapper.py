#!/usr/bin/env python3
"""Genera un wrapper .luau que embebe la fuente del módulo ofuscado + hooks
(loadstring interceptor, stubs Roblox) para correrlo en el CLI luau crudo."""
import sys


def long_string(s: str) -> str:
    level = 0
    while ("]" + "=" * level + "]") in s:
        level += 1
    eq = "=" * level
    return "[" + eq + "[\n" + s + "]" + eq + "]"


HOOK = r"""
-- ================= interceptor embebido =================
local real_loadstring = loadstring
local captured = 0

local function hook_loadstring(source, chunkname)
        captured = captured + 1
        print("\n==LOADSTRING_" .. captured .. "== chunkname=" .. tostring(chunkname) .. " len=" .. (source and #source or -1))
        print(source)
        print("==END_LOADSTRING_" .. captured .. "==\n")
        local real = real_loadstring(source, tostring(chunkname or "=cap" .. captured))
        if not real then
                return function(...) return function() end end, nil
        end
        -- chunk encadenado: hereda el env del LLAMADOR para que los canaries
        -- que planta cada capa persistan en el mismo proxy/genv
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
                if k == "HttpGet" then return function() return "" end end
                if k == "PlaceId" then return 2753915549 end
                if k == "GameId" then return 994732206 end
                if k == "RobloxLocaleId" then return "en-us" end
                if k == "JobId" then return "0f0f0f0f-0f0f-0f0f-0f0f-0f0f0f0f0f0f" end
                if k == "CreatorId" then return 158323776 end
                if k == "CreatorType" then return "User" end
                if k == "Name" then return "Blox Fruits" end
                if k == "PrivateServerId" then return "" end
                if k == "PrivateServerOwnerId" then return 0 end
                if k == "Players" then return Players end
                if k == "LocalPlayer" then return localplayer_stub end
                return function() end
        end,
})
local Players = stub_service("Players")
local localplayer_stub = setmetatable({ Name = "Player", UserId = 123456789, DisplayName = "Player" }, {
        __index = function() return function() end end,
        __tostring = function() return "Player" end,
})

local genv = getfenv()
genv._ENV = genv
genv.game = game
genv.workspace = stub_service("Workspace")
genv.loadstring = hook_loadstring
genv.Players = Players
genv.spawn = function(f) end -- descartado: loops infinitos con wait no-yield
genv.wait = function() end
genv.delay = function(_, f) end
genv.tick = os.clock
genv.time = os.time
genv.writefile = function() end
genv.readfile = function() return "" end
genv.isfile = function() return false end
genv.isfolder = function() return false end
genv.makefolder = function() end
genv.listfiles = function() return {} end
genv.identifyexecutor = function() return "luau" end
genv.getgenv = function() return genv end
genv.getrenv = function() return genv end
genv.http_request = function(t) return { Body = "{}", StatusCode = 200, Headers = {} } end
genv.request = genv.http_request
genv.setclipboard = function() end
genv.shared = {}
-- spawn/delay/defer: se DESCARTAN (con wait no-yield ejecutarian loops infinitos)
local task_stub = setmetatable({}, { __index = function(_, k)
        if k == "clock" then return function() return 0 end end
        return function() end
end })
genv.task = task_stub
genv.Instance = setmetatable({}, { __index = function() return function() return setmetatable({}, { __index = function() return function() end end }) end end })
genv.Enum = setmetatable({}, { __index = function() return setmetatable({}, { __index = function() return function() end end }) end })
genv.Color3 = { fromRGB = function() return {} end, new = function() return {} end }
genv.Vector2 = { new = function() return {} end }
genv.Vector3 = { new = function() return {} end }
genv.UDim2 = { new = function() return {} end }
genv.CFrame = { new = function() return {} end }
genv.TweenInfo = { new = function() return {} end }
genv.Random = { new = function() return { NextNumber = function() return 0 end } end }
genv.Drawing = setmetatable({}, { __index = function() return function() return { Remove = function() end, Visible = true } end end })
genv.getconnections = function() return {} end
genv.hookfunction = function(f) return f end
genv.getcallingcript = function() return nil end
genv.getsenv = function() return genv end
genv.checkcaller = function() return false end
local print_budget = 50
local real_print = print
local function budget_print(...)
	if print_budget > 0 then
		print_budget = print_budget - 1
		if select("#", ...) == 1 and select(1, ...) == nil then
			local names = {}
			for lvl = 2, 8 do
				local ok, nm = pcall(debug.info, lvl, "n")
				if not ok or nm == nil then break end
				names[#names + 1] = tostring(nm)
			end
			real_print("[NILPRINT] frames:", table.concat(names, " > "))
			real_print(debug.traceback(nil, 2))
		else
			real_print(...)
		end
	elseif print_budget == 0 then
		print_budget = -1
		real_print("[...] print budget agotado, corto el output")
	end
end
genv.print = budget_print
genv.warn = budget_print
-- canaries nil: flujo real del executor
genv.FireServer = nil

local fn, err = real_loadstring(__TARGET__, "=target")
assert(fn, "compile error: " .. tostring(err))
-- proxy env: registra globals leidos que valen nil
local nilreads = {}
local proxy = setmetatable({}, {
        __index = function(_, k)
                local v = genv[k]
                if v == nil then
                        if not nilreads[k] then
                                nilreads[k] = true
                                print("[NILREAD->0] " .. tostring(k))
                                print(debug.traceback("[stack de " .. tostring(k) .. "]", 2))
                        end
                        return 0 -- canary numerico por defecto
                end
                return v
        end,
        __newindex = function(_, k, v)
                print("[SET] " .. tostring(k) .. " = " .. type(v))
                genv[k] = v
        end,
})
setfenv(fn, proxy)
local ok, rerr = xpcall(fn, function(e)
        return tostring(e) .. "\n" .. debug.traceback(nil, 2)
end)
print("\n==RUN== ok=" .. tostring(ok) .. " err=" .. tostring(rerr) .. " loadstrings=" .. captured)
"""


def main():
    target = sys.argv[1]
    out = sys.argv[2]
    src = open(target, encoding="utf-8", errors="surrogateescape").read()
    wrapped = "local __TARGET__ = " + long_string(src) + "\n" + HOOK
    open(out, "w", encoding="utf-8", errors="surrogateescape").write(wrapped)
    print("[+] wrapper:", out, len(wrapped), "bytes")


if __name__ == "__main__":
    main()
