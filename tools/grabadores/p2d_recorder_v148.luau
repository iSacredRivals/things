--[[
  GRABADOR Path2D — desbloquea la "stage key" de Cokeboys V1.8 / Luraph v14.8
  (script de prueba message.txt, 2.7 MB)

  CÓMO USARLO:
  1) Abre tu executor (Wave/Synapse/etc.) en el juego donde uses el script,
     o Roblox Studio (con Run Luau / consola).
  2) Pega ESTE script completo y ejecútalo (tarda <1 segundo).
  3) Copia TODO lo que imprima (desde ==P2D== hasta ==END==) y mándamelo.

  Qué hace: reproduce la sonda anti-tamper EXACTA del script
  (Frame 216x178 + Path2D con 3 control points concretos) y graba las 12
  respuestas REALES del motor de Roblox, con la precisión exacta que Luraph
  mezcla en la clave de decodificación. Sin estas respuestas, el decodificador
  del VM entra en un bucle infinito y no se recupera más código.
]]

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

local function fmt17(n)
	return string.format("%.17g", n)
end

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
	local function add(line)
		table.insert(lines, line)
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
	print("==P2D" .. tag .. "==")
	for _, l in ipairs(lines) do
		print(l)
	end
	print("==END" .. tag .. "==")
end

-- 1) la réplica EXACTA de la sonda del script (ScreenGui sin parent)
local sg, p2d = setup(nil)
record("", p2d)

-- 2) variante de respaldo: ScreenGui dentro del DataModel (por si la
--    variante exacta da errores en tu entorno)
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
print("[*] listo — copia TODO el bloque de arriba y pásamelo")
