--[[
  GRABADOR Path2D — desbloquea la "stage key" de este script (Luraph key-gated)

  1) Ejecuta ESTE script en tu executor o Roblox Studio (dura <1 s).
  2) Copia TODO lo que imprima (desde ==P2D== hasta ==END==) y pásalo.
]]

local QUERIES = {
	{ "GetPositionOnCurve", 0.75 },
	{ "GetPositionOnCurve", 0.60000002384185791 },
	{ "GetTangentOnCurve", 0.1428571492433548 },
	{ "GetTangentOnCurve", 0.875 },
	{ "GetPositionOnCurveArcLength", 0.63636362552642822 },
	{ "GetPositionOnCurveArcLength", 0.60000002384185791 },
	{ "GetTangentOnCurveArcLength", 0.5 },
	{ "GetTangentOnCurveArcLength", 0.80000001192092896 },
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
	fr.Size = UDim2.new(0, 222, 0, 119)
	fr.Parent = sg
	local p2d = Instance.new("Path2D")
	p2d.Parent = fr
	p2d:SetControlPoints({ Path2DControlPoint.new(UDim2.new(0.25, 4, 0, -6), UDim2.new(0.0625, 1, 0, -1), UDim2.new(0, 0, 0, 0)), Path2DControlPoint.new(UDim2.new(0, -9, 0, -8), UDim2.new(0, -1, 0, -1), UDim2.new(0, -5, 0.125, 2)), Path2DControlPoint.new(UDim2.new(0, 6, 0, 1), UDim2.new(0, -6, -0.125, -6), UDim2.new(0, 0, 0, 0)) })
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

local ALL = {}
local realPrint = print
print = function(...)
	local parts = {}
	for i = 1, select("#", ...) do parts[i] = tostring(select(i, ...)) end
	local line = table.concat(parts, "\t")
	table.insert(ALL, line)
	realPrint(line)
end

local sg, p2d = setup(nil)
record("", p2d)
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
local TEXT = table.concat(ALL, "\n")
realPrint("\n[*] copiando al portapapeles...")
local okClip = pcall(function()
	if setclipboard then setclipboard(TEXT) end
end)
if not okClip then
	pcall(function()
		if toclipboard then toclipboard(TEXT) end
	end)
	pcall(function()
		if syn and syn.set_clipboard then syn.set_clipboard(TEXT) end
	end)
end
realPrint(okClip and "[+] LISTO: ya lo tenés en el portapapeles — pegalo en el chat" or "[!] sin clipboard: copiá a mano todo el bloque de arriba")
realPrint("[*] (respaldo: también se intentó subir a paste.rs y filebin)")
pcall(function()
	if http_request then
		http_request({ Url = "https://paste.rs/", Method = "POST", Body = TEXT, Headers = { ["Content-Type"] = "text/plain" } })
	end
end)
pcall(function()
	if request then
		request({ Url = "https://paste.rs/", Method = "POST", Body = TEXT, Headers = { ["Content-Type"] = "text/plain" } })
	end
end)
