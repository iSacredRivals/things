--[[
	GRABADOR LURAPH · TODO-EN-UNO · AUTOGUARDADO
	============================================
	Graba todo lo que hace falta para terminar los decodes pendientes:

	  1) ==P2D==  →  la "stage key" de Cokeboys V1.8 (Luraph v14.8):
	      réplica EXACTA de su sonda (Frame 216x178 + Path2D con 3
	      control points concretos) y las 12 respuestas REALES del
	      motor. Sin estas respuestas el decoder del VM entra en un
	      bucle infinito y no sale más código.
	  2) ==ENV==  →  los valores vivos del entorno que valida la VM
	      de Hermenos Hub (Luraph v14.5.2): typeof / type / metatables
	      / frozen de los globals, enumeración de getfenv() y locale.

	Y LO GUARDA SOLO (no tienes que copiar nada a mano):
	  - writefile  →  "grabador_luraph.txt" en la CARPETA DE ARCHIVOS
	    de tu executor (pestaña Files / Archivos del executor)
	  - setclipboard  →  todo el contenido al portapapeles
	  - si no hay writefile (p.ej. Roblox Studio), copia el bloque
	    impreso en la consola

	CÓMO USARLO:
	  1) Abre tu executor (Wave / Synapse / Delta / Fluxus / etc.)
	     EN EL JUEGO donde usas el script (mismo executor donde se
	     queda colgado — las respuestas salen de SU motor).
	  2) Ejecuta ESTE archivo completo (tarda menos de 1 segundo).
	  3) Busca "grabador_luraph.txt" en la pestaña de archivos del
	     executor y MÁNDAME ESE ARCHIVO.
]]

-- ================= acumulador de salida =================
local OUT = {}
local function line(s)
	OUT[#OUT + 1] = s
	print(s)
end

local function fmt17(n)
	return string.format("%.17g", n)
end

-- ================= 1) SONDA P2D (Cokeboys v14.8) =================
local QUERIES = {
	{ "GetPositionOnCurve", 0.4285714328289032 },
	{ "GetPositionOnCurve", 0.20000000298023224 },
	{ "GetPositionOnCurve", 0.25 },
	{ "GetPositionOnCurve", 0.38461539149284363 },
	{ "GetTangentOnCurve", 0.20000000298023224 },
	{ "GetTangentOnCurve", 0.20000000298023224 }, -- el script la repite
	{ "GetTangentOnCurve", 0.2142857164144516 },
	{ "GetPositionOnCurveArcLength", 0.1666666716337204 },
	{ "GetPositionOnCurveArcLength", 0.80000001192092896 },
	{ "GetTangentOnCurveArcLength", 0.3333333432674408 },
	{ "GetTangentOnCurveArcLength", 0.53846156597137451 },
}

local function encode(v)
	local t = typeof(v)
	if t == "number" then
		return "n:" .. fmt17(v)
	elseif t == "UDim2" then
		return string.format("u:%.17g,%.17g,%.17g,%.17g", v.X.Scale, v.X.Offset, v.Y.Scale, v.Y.Offset)
	elseif t == "Vector2" then
		return string.format("v:%.17g,%.17g", v.X, v.Y)
	end
	return "?" .. tostring(v)
end

local function setup(parentScreenGui)
	local sg = Instance.new("ScreenGui")
	if parentScreenGui then
		sg.Parent = parentScreenGui
	end
	local fr = Instance.new("Frame")
	fr.Position = UDim2.new(0, 0, 0, 0)
	fr.Size = UDim2.new(0, 216, 0, 178)
	fr.Parent = sg
	local p2d = Instance.new("Path2D")
	p2d.Parent = fr
	p2d:SetControlPoints({
		Path2DControlPoint.new(UDim2.new(0, -7, 0.125, 0), UDim2.new(0.125, 5, 0, 0), UDim2.new(0, -7, 0, -4)),
		Path2DControlPoint.new(UDim2.new(0.5, 5, 0, 6), UDim2.new(0, 0, 0, 0), UDim2.new(0, 0, 0, 0)),
		Path2DControlPoint.new(UDim2.new(0.25, -8, 0, -7), UDim2.new(0, 0, 0, 0), UDim2.new(-0.125, 4, 0, -1)),
	})
	return sg, p2d
end

local function record(tag, p2d)
	local lines = {}
	local function add(l)
		lines[#lines + 1] = l
	end
	local ok, err = pcall(function()
		add("GetLength\t" .. encode(p2d:GetLength()))
	end)
	if not ok then
		add("GetLength\tERROR " .. tostring(err))
	end
	for _, q in ipairs(QUERIES) do
		local name, arg = q[1], q[2]
		local key = name .. "|" .. fmt17(arg)
		local ok2, res = pcall(function()
			return p2d[name](p2d, arg)
		end)
		if ok2 then
			add(key .. "\t" .. encode(res))
		else
			add(key .. "\tERROR " .. tostring(res))
		end
	end
	line("==P2D" .. tag .. "==")
	for _, l in ipairs(lines) do
		line(l)
	end
	line("==END" .. tag .. "==")
end

-- 1a) réplica EXACTA de la sonda del script (ScreenGui sin parent)
local sg, p2d = setup(nil)
record("", p2d)

-- 1b) variante de respaldo: ScreenGui dentro del DataModel
local okAll = pcall(function()
	local sg2, p2d2 = setup(game:GetService("CoreGui"))
	record("GUI", p2d2)
	sg2:Destroy()
end)
if not okAll then
	pcall(function()
		local sg3, p2d3 = setup(workspace)
		record("WS", p2d3)
		sg3:Destroy()
	end)
end
sg:Destroy()

-- ================= 2) ENTORNO VIVO (Hermenos v14.5) =================
line("==ENV==")

local ex = "unknown"
pcall(function() ex = identifyexecutor() end)
line("executor\t" .. tostring(ex))

local okd, d = pcall(function() return os.date("%Y-%m-%d %H:%M:%S") end)
line("date\t" .. ((okd and d) or "?"))

local okl, loc = pcall(function() return game.RobloxLocaleId end)
line("RobloxLocaleId\t" .. ((okl and tostring(loc)) or "ERR"))

local okl2, loc2 = pcall(function()
	return game:GetService("LocalizationService").RobloxLocaleId
end)
line("LS_RobloxLocaleId\t" .. ((okl2 and tostring(loc2)) or "ERR"))

local E = getfenv()
do
	local okm, emt = pcall(getmetatable, E)
	if okm and emt == nil then
		line("env_meta\tnil")
	elseif okm and type(emt) == "string" then
		line("env_meta\tprotected:" .. emt)
	elseif okm and type(emt) == "table" then
		local bits = {}
		for _, k in ipairs({ "__index", "__newindex", "__tostring", "__metatable" }) do
			bits[#bits + 1] = (rawget(emt, k) ~= nil) and k or "-"
		end
		line("env_meta\ttable[" .. table.concat(bits, ",") .. "]")
	else
		line("env_meta\tERR")
	end
end

local NAMES = {
	-- núcleo Roblox
	"game", "workspace", "script", "Instance", "Enum", "shared", "plugin",
	"Vector2", "Vector3", "Vector2int16", "Vector3int16", "UDim", "UDim2",
	"CFrame", "Color3", "ColorSequence", "NumberSequence", "NumberRange",
	"Rect", "Region3", "Faces", "Axises", "PhysicalProperties", "TweenInfo",
	"Ray", "Random", "DateTime", "Font", "Path2DControlPoint",
	-- librerías
	"string", "table", "math", "os", "coroutine", "task", "bit32", "utf8",
	"buffer", "debug", "io", "_G",
	-- funciones base
	"type", "typeof", "tostring", "tonumber", "pcall", "xpcall", "select",
	"unpack", "rawget", "rawset", "rawequal", "rawlen", "setmetatable",
	"getmetatable", "assert", "error", "ipairs", "pairs", "next", "require",
	"getfenv", "setfenv", "loadstring", "gcinfo", "collectgarbage",
	"newproxy", "print", "warn", "spawn", "wait", "delay", "tick", "time",
	"elapsedTime", "settings", "UserSettings",
	-- executor
	"Drawing", "getgenv", "getrenv", "writefile", "readfile", "appendfile",
	"listfiles", "isfile", "isfolder", "makefolder", "setclipboard",
	"getclipboard", "identifyexecutor", "syn", "fluxus", "delta",
	"checkcaller", "hookfunction", "getconnections", "getreg",
}

for _, name in ipairs(NAMES) do
	local ok, v = pcall(function()
		return rawget(E, name)
	end)
	if not ok or v == nil then
		line("g\t" .. name .. "\tnil")
	else
		local t1 = type(v)
		local t2 = typeof(v)
		local mts = "nil"
		local okm, mt = pcall(getmetatable, v)
		if okm then
			if mt == nil then
				mts = "nil"
			elseif type(mt) == "string" then
				mts = "protected:" .. mt
			elseif type(mt) == "table" then
				local bits = {}
				for _, k in ipairs({ "__index", "__newindex", "__tostring", "__metatable" }) do
					bits[#bits + 1] = (rawget(mt, k) ~= nil) and k or "-"
				end
				mts = "table[" .. table.concat(bits, ",") .. "]"
			else
				mts = type(mt)
			end
		else
			mts = "ERR"
		end
		local extra = ""
		if t1 == "table" then
			local okf, fr = pcall(table.isfrozen, v)
			extra = "\tfrozen:" .. ((okf and tostring(fr)) or "?")
		end
		line("g\t" .. name .. "\t" .. t1 .. "\t" .. t2 .. "\tmt:" .. mts .. extra)
	end
end

-- enumeración de getfenv() (lo que la VM v14.5 chequea con pairs)
do
	local names = {}
	pcall(function()
		for k in pairs(getfenv()) do
			names[#names + 1] = tostring(k)
		end
	end)
	table.sort(names)
	local row = {}
	local function flush()
		if #row > 0 then
			line("env_globals\t" .. table.concat(row, " "))
			row = {}
		end
	end
	for _, n in ipairs(names) do
		row[#row + 1] = n
		if #row >= 12 then
			flush()
		end
	end
	flush()
	line("env_globals_count\t" .. tostring(#names))
end
line("==ENDENV==")

-- ================= 3) AUTOGUARDADO =================
local data = table.concat(OUT, "\n") .. "\n"
local fname = "grabador_luraph.txt"

print("=====================================================")
local okw = pcall(function()
	writefile(fname, data)
end)
if okw then
	print("[+] GUARDADO: '" .. fname .. "' en la carpeta de archivos de tu executor")
	local okv, back = pcall(function()
		return readfile(fname)
	end)
	if okv and back == data then
		print("[+] verificado (" .. #data .. " bytes re-leídos) — mándame ese archivo")
	elseif okv then
		print("[~] re-leído " .. #back .. " bytes (no coincide 1:1, revisa el archivo)")
	else
		print("[-] se escribió, pero readfile falló al verificar")
	end
else
	print("[-] tu entorno no tiene writefile (¿Studio?): copia a mano el bloque de arriba")
end

local okc = pcall(function()
	setclipboard(data)
end)
if okc then
	print("[+] TODO el contenido copiado al PORTAPAPELES")
end

print("[*] LISTO — necesito el archivo '" .. fname .. "' completo (bloques ==P2D== y ==ENV==)")
