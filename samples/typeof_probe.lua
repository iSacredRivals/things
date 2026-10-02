-- typeof probe: runs inside the envlog environment
local names = {
	"DockWidgetPluginGuiInfo","string","UniqueId","CFrame","_VERSION","UDim2","CFrameCurveKey","Rect","os","table",
	"TweenInfo","buffer","task","Vector3","RaycastParams","Vector3int16","debug","NumberSequence","Random","http",
	"workspace","Game","ColorSequence","bit32","CatalogSearchParams","Vector2int16","Region3int16","game","Faces",
	"OverlapParams","Path2DControlPoint","SecurityCapabilities","utf8","Workspace","Content","_G","PathWaypoint","Region3",
	"NumberSequenceKeypoint","Drawing","vector","Color3","math","crypt","coroutine","PhysicalProperties","NumberRange",
	"FloatCurveKey","shared","SharedTable","Instance","RotationCurveKey","DateTime","Enum",
}
for _, n in ipairs(names) do
	local v = rawget(getfenv(), n)
	if v == nil then
		v = getfenv()[n]
		print(n .. ": <metatable-resolved> type=" .. type(v) .. " typeof=" .. tostring(typeof(v)))
	else
		print(n .. ": raw type=" .. type(v) .. " typeof=" .. tostring(typeof(v)))
	end
end
print("DONE")
