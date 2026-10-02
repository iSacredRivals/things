-- interceptor.luau — corre un módulo ofuscado (Prometheus-style) en luau crudo
-- y captura TODO lo que llega a loadstring en stdout entre marcadores.
-- Uso: luau interceptor.luau <archivo> > dump.txt

local target = ...
assert(target, "falta el archivo")
local src = loadstring("return readfile and 1") -- placeholder, luau no tiene readfile

-- luau CLI: leer el archivo con io? No hay io. Usamos arg del CLI: el propio
-- runtime de luau ejecuta archivos; para leer usamos loadfile? No existe.
-- Solución: el runner embebe el código.

local DUMP = {}
local function marker(i, s)
	DUMP[i] = s
	io_write = nil
end

-- stub mínimo de Roblox para pasar las primeras llamadas
local services = {}
local game = setmetatable({ game = true }, {
	__index = function(t, k)
		if k == "GetService" then
			return function(_, name)
				if not services[name] then
					services[name] = setmetatable({}, { __index = function() return function() end end })
				end
				return services[name]
			end
		end
		if k == "HttpGet" then return function() return "" end end
		if k == "PlaceId" then return 2753915549 end
		if k == "GameId" then return 994732206 end
		if k == "RobloxLocaleId" then return "en-us" end
		return function() end
	end,
	__call = function() return game end,
})
local Players = setmetatable({}, { __index = function() return function() end end })

local real_loadstring = loadstring
local captured = 0
local function hook_loadstring(source, chunkname)
	captured = captured + 1
	print("\n==LOADSTRING_" .. captured .. "== chunkname=" .. tostring(chunkname) .. " len=" .. (source and #source or -1))
	print(source)
	print("==END_LOADSTRING_" .. captured .. "==\n")
	-- devolver una función no-op que devuelve tabla vacía inofensiva
	return function(...)
		return function() end
	end
end

-- el env del chunk: globals reales + game + loadstring hook
local genv = getfenv()
genv.game = game
genv.workspace = setmetatable({}, { __index = function(_, k) return game[k] end })
genv.loadstring = hook_loadstring
genv.Players = Players
genv.spawn = function(f) return f() end
genv.wait = function() end
genv.tick = os.clock
genv.writefile = function() end
genv.readfile = function() return "" end
genv.isfile = function() return false end
genv.identifyexecutor = function() return "luau" end
genv.getgenv = function() return genv end
genv.http_request = function(t) return { Body = "{}", StatusCode = 200 } end
genv.request = genv.http_request

local fn, err
do
	local f = io.open(target, "r")
	assert(f, "no puedo abrir " .. tostring(target))
	local content = f:read("*a")
	f:close()
	fn, err = real_loadstring(content, "=" .. target)
end
assert(fn, "compile error: " .. tostring(err))

setfenv(fn, genv)
local ok, rerr = pcall(fn)
print("\n==RUN== ok=" .. tostring(ok) .. " err=" .. tostring(rerr) .. " loadstrings=" .. captured)
