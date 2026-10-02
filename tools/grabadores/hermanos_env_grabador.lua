-- GRABADOR DE ENTORNO (env dump) para Hermanos Hub
-- Ejecuta esto en tu executor (Delta) en cualquier juego, espera <1 segundo
-- y pégame TODO lo que salga entre ==ENV== y ==END==
-- (también se copia al portapapeles y se intenta subir a paste.rs)

local function safe(fn, ...)
	local ok, res = pcall(fn, ...)
	if ok then return tostring(res) end
	return "ERR:" .. tostring(res):sub(1, 60)
end

local lines = {}
local function add(s) lines[#lines + 1] = s end

add("==ENV==")
add("executor=" .. safe(identifyexecutor))
add("executorname=" .. safe(getexecutorname))

-- 1) getfenv() con typeof, en ORDEN RAW de iteración (importante)
local seen = {}
local n = 0
for k, v in pairs(getfenv()) do
	n = n + 1
	seen[#seen + 1] = tostring(n) .. "|" .. tostring(k) .. "|" .. typeof(v)
end
add("getfenv_count=" .. n)
add("--getfenv_raw_order--")
for _, l in ipairs(seen) do add(l) end

-- 2) getfenv() ordenado (legible)
local names = {}
for k in pairs(getfenv()) do names[#names + 1] = tostring(k) end
table.sort(names)
add("--getfenv_sorted--")
add(table.concat(names, ","))

-- 3) getgenv()
local gn = {}
local gn2 = 0
for k in pairs(getgenv()) do
	gn2 = gn2 + 1
	gn[#gn + 1] = tostring(k)
end
table.sort(gn)
add("getgenv_count=" .. gn2)
add("--getgenv_sorted--")
add(table.concat(gn, ","))

-- 4) probes puntuales que el VM revisa
add("rawget_DateTime=" .. tostring(rawget(getfenv(), "DateTime")))
add("rawget_Enums=" .. tostring(rawget(getfenv(), "Enums")))
add("rawget_Game=" .. tostring(rawget(getfenv(), "Game")))
add("rawget_Workspace=" .. tostring(rawget(getfenv(), "Workspace")))
add("typeof_script=" .. safe(function() return typeof(script) end))
add("mt_env=" .. safe(function() return tostring(getmetatable(getfenv())) end))

-- 5) entorno DENTRO de un loadstring (como corre la cadena real)
local inner = loadstring([[
	local t = {}
	local c = 0
	for k in pairs(getfenv()) do c = c + 1; t[#t+1] = tostring(k) end
	table.sort(t)
	return c, table.concat(t, ",")
]])
if inner then
	local ok, c, s = pcall(inner)
	if ok then
		add("loadstring_env_count=" .. tostring(c))
		add("--loadstring_env_sorted--")
		add(tostring(s))
	else
		add("loadstring_env=ERR:" .. tostring(c):sub(1, 80))
	end
else
	add("loadstring_env=COMPILE_ERR")
end

add("==END==")

local out = table.concat(lines, "\n")
print(out)

-- portapapeles
pcall(function() setclipboard(out) end)
pcall(function() toclipboard(out) end)
pcall(function()
	local syn = syn or {}
	if syn.set_clipboard then syn.set_clipboard(out) end
end)

-- subida de respaldo
pcall(function()
	local req = request or http_request or (http and http.request)
	if req then
		local res = req({
			Url = "https://paste.rs",
			Method = "POST",
			Body = out,
		})
		if res and res.Body then print("PASTE_RS=" .. tostring(res.Body):sub(1, 120)) end
	end
end)
pcall(function()
	local req = request or http_request or (http and http.request)
	if req then
		local res = req({
			Url = "https://filebin.net/hermanos-env-01/env_dump.txt",
			Method = "POST",
			Body = out,
		})
		if res then print("FILEBIN_OK=" .. tostring(res.StatusCode)) end
	end
end)
