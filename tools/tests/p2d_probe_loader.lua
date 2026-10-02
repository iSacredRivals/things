-- Clean replica of the LOADER's (obf_5) exact Path2D probe:
-- Frame 193x224, 6 control points, 13 queries in the loader's own order.
-- Runs under envlog (offline engine). With --cfg p2d_check=true the engine
-- prints \0P2DCHECK lines comparing the offline model against the recorded
-- (real-device) answers loaded from the cache.

local ScreenGui = Instance.new("ScreenGui")
local Frame = Instance.new("Frame")
Frame.Position = UDim2.new(0, 0, 0, 0)
Frame.Size = UDim2.new(0, 193, 0, 224)
Frame.Parent = ScreenGui
local Path = Instance.new("Path2D")
Path.Parent = Frame
Path:SetControlPoints({
	Path2DControlPoint.new(UDim2.new(0.0625, 6, 0.125, 7), UDim2.new(0, -3, 0, 5), UDim2.new(0, 0, 0, 0)),
	Path2DControlPoint.new(UDim2.new(0, 9, 0.25, -6), UDim2.new(0, 0, 0, 0), UDim2.new(0, 0, 0, 0)),
	Path2DControlPoint.new(UDim2.new(0.25, 1, 0.0625, 3), UDim2.new(0, -5, 0, 0), UDim2.new(0, 0, 0, 5)),
	Path2DControlPoint.new(UDim2.new(0.125, -6, 0.25, -3), UDim2.new(0.0625, -7, 0, -1), UDim2.new(0, 5, 0, -6)),
	Path2DControlPoint.new(UDim2.new(0, 3, 0, 5), UDim2.new(0, 0, 0, 0), UDim2.new(0, 0, 0, 0)),
	Path2DControlPoint.new(UDim2.new(0.25, 2, 0.4375, -6), UDim2.new(0, 7, 0, -3), UDim2.new(-0.125, -1, 0, -4)),
})

local function g17(x) return string.format("%.17g", x) end
local out = {}

local ok, len = pcall(function() return Path:GetLength() end)
out[#out + 1] = "GetLength\tn:" .. g17(ok and len or 0)

local posCalls = {
	{ "GetPositionOnCurve", 0.75 },
	{ "GetPositionOnCurve", 0.5 },
	{ "GetPositionOnCurve", 0.8461538553237915 },
}
for _, c in ipairs(posCalls) do
	local ok2, u = pcall(function() return Path[c[1]](Path, c[2]) end)
	if ok2 and u then
		out[#out + 1] = c[1] .. "|" .. g17(c[2]) .. "\tu:"
			.. g17(u.X.Scale) .. "," .. g17(u.X.Offset) .. ","
			.. g17(u.Y.Scale) .. "," .. g17(u.Y.Offset)
	else
		out[#out + 1] = c[1] .. "|" .. g17(c[2]) .. "\tERR:" .. tostring(u)
	end
end

local tanCalls = {
	{ "GetTangentOnCurve", 0.75 },
	{ "GetTangentOnCurve", 0.5 },
	{ "GetTangentOnCurve", 0.5 },
	{ "GetTangentOnCurve", 0.18181818723678589 },
}
for _, c in ipairs(tanCalls) do
	local ok2, v = pcall(function() return Path[c[1]](Path, c[2]) end)
	if ok2 and v then
		out[#out + 1] = c[1] .. "|" .. g17(c[2]) .. "\tv:" .. g17(v.X) .. "," .. g17(v.Y)
	else
		out[#out + 1] = c[1] .. "|" .. g17(c[2]) .. "\tERR:" .. tostring(v)
	end
end

local arcCalls = {
	{ "GetPositionOnCurveArcLength", 0.40000000596046448 },
	{ "GetPositionOnCurveArcLength", 0.28571429848670959 },
	{ "GetTangentOnCurveArcLength", 0.8571428656578064 },
	{ "GetTangentOnCurveArcLength", 0.69999998807907104 },
	{ "GetTangentOnCurveArcLength", 0.69999998807907104 },
}
for _, c in ipairs(arcCalls) do
	local ok2, r = pcall(function() return Path[c[1]](Path, c[2]) end)
	if ok2 and r then
		if typeof(r) == "UDim2" then
			out[#out + 1] = c[1] .. "|" .. g17(c[2]) .. "\tu:"
				.. g17(r.X.Scale) .. "," .. g17(r.X.Offset) .. ","
				.. g17(r.Y.Scale) .. "," .. g17(r.Y.Offset)
		else
			out[#out + 1] = c[1] .. "|" .. g17(c[2]) .. "\tv:" .. g17(r.X) .. "," .. g17(r.Y)
		end
	else
		out[#out + 1] = c[1] .. "|" .. g17(c[2]) .. "\tERR:" .. tostring(r)
	end
end

print("==P2D-LOADER-MODEL==")
for _, l in ipairs(out) do
	print(l)
end
print("==P2D-LOADER-MODEL-END==")
