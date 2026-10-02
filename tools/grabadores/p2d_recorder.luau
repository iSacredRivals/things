--[[
  GRABADOR Path2D — desbloquea la "stage key" de deobf_pls.lua (Luraph v15)

  CÓMO USARLO:
  1) Abre tu executor (Wave) en el juego donde uses el script protegido,
     o Roblox Studio (ServerStorage → click derecho → "Run Luau" / o pégalo
     en la consola de Studio si la tienes).
  2) Pega ESTE script completo y ejecútalo.
  3) Copia TODO lo que imprima (desde ==P2D== hasta ==END==) y mándamelo.

  Qué hace: reproduce la sonda anti-tamper del script (Frame 118x255 +
  Path2D con 3 control points) y graba las 11 respuestas REALES del motor
  de Roblox, con la precisión exacta que Luraph mezcla en su clave.
]]

local QUERIES = {
	{ "GetPositionOnCurve", 0.2142857164144516 },
	{ "GetPositionOnCurve", 0.55555558204650879 },
	{ "GetPositionOnCurve", 0.92857140302658081 },
	{ "GetTangentOnCurve", 0.1666666716337204 },
	{ "GetTangentOnCurve", 0.80000001192092896 },
	{ "GetTangentOnCurve", 0.625 },
	{ "GetPositionOnCurveArcLength", 0.625 },
	{ "GetPositionOnCurveArcLength", 0.66666668653488159 },
	{ "GetTangentOnCurveArcLength", 0.5 },
	{ "GetTangentOnCurveArcLength", 0.5625 },
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
	fr.Size = UDim2.new(0, 118, 0, 255)
	fr.Parent = sg
	local p2d = Instance.new("Path2D")
	p2d.Parent = fr
	p2d:SetControlPoints({
		Path2DControlPoint.new(UDim2.new(0, 9, 0, -8), UDim2.new(0, 0, 0, 0), UDim2.new(0, -7, 0, -7)),
		Path2DControlPoint.new(UDim2.new(0, 0, 0.3125, -2), UDim2.new(-0.0625, -5, 0, 6), UDim2.new(0, -8, -0.125, 7)),
		Path2DControlPoint.new(UDim2.new(0.25, 2, 0.3125, 1), UDim2.new(0, 0, 0, 0), UDim2.new(0, -4, 0, 1)),
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
