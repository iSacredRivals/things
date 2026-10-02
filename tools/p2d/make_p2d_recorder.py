"""Generate a Path2D recorder .luau from a RAW deobf run output (--raw file).

The raw output holds the Path2D probe as traced statements plus the \\0P2D
query log - everything needed to reproduce the probe bit-exactly in a real
client. The emitted recorder prints ==P2D== ... ==END== which feeds
parse_p2d_paste.py --out <input>.path2d.

Usage:
  python3 deob.py <script> --no-devirt --raw /tmp/raw.txt ...
  python3 make_p2d_recorder.py /tmp/raw.txt -o recorder.luau
"""
import re
import sys

RAW = sys.argv[1] if len(sys.argv) > 1 else ''
OUT = sys.argv[sys.argv.index('-o') + 1] if '-o' in sys.argv else 'p2d_recorder.luau'

text = open(RAW, encoding='utf-8', errors='replace').read()

# 1) control points: the traced SetControlPoints statement
m = re.search(r'Path2D(?::|\.)SetControlPoints\(\s*(\{.*?\})\s*\)', text, re.S)
if not m:
    sys.exit("[!] no SetControlPoints in the raw output (not a Path2D-keyed script?)")
control_points = m.group(1)

# 2) frame: the Size/Position assignments just before the Path2D parent line
fsize = re.search(r'Frame\.Size = (UDim2\.new\([^)]*\))', text)
fpos = re.search(r'Frame\.Position = (UDim2\.new\([^)]*\))', text)

# 3) queries: the \0P2D log (authoritative order and t values)
queries = re.findall(r'\x00P2D (Get(?:Position|Tangent)\w*)\|([\d.eE+-]+)\t', text)
if not queries:
    # no \0P2D log (e.g. everything replayed from cache): fall back to the
    # traced query statements
    queries = re.findall(r'Path2D(?::|\.)(Get(?:Position|Tangent)\w*)\(([\d.eE+-]+)\)', text)
if not queries:
    sys.exit("[!] no curve queries found")

qlines = "\n".join('\t{ "%s", %s },' % (n, t) for n, t in queries)

TEMPLATE = '''--[[
  GRABADOR Path2D — desbloquea la "stage key" de este script (Luraph key-gated)

  1) Ejecuta ESTE script en tu executor o Roblox Studio (dura <1 s).
  2) Copia TODO lo que imprima (desde ==P2D== hasta ==END==) y pásalo.
]]

local QUERIES = {
__QUERIES__
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
	fr.Position = __POS__
	fr.Size = __SIZE__
	fr.Parent = sg
	local p2d = Instance.new("Path2D")
	p2d.Parent = fr
	p2d:SetControlPoints(__CPS__)
	return sg, p2d
end

local function record(tag, p2d)
	local lines = {}
	local function add(line)
		table.insert(lines, line)
	end
	local ok, err = pcall(function()
		add("GetLength\\t" .. encode(p2d:GetLength()))
	end)
	if not ok then
		add("GetLength\\tERROR " .. tostring(err))
	end
	for _, q in ipairs(QUERIES) do
		local name, arg = q[1], q[2]
		local key = name .. "|" .. fmt17(arg)
		local ok2, res = pcall(function()
			return p2d[name](p2d, arg)
		end)
		if ok2 then
			add(key .. "\\t" .. encode(res))
		else
			add(key .. "\\tERROR " .. tostring(res))
		end
	end
	print("==P2D" .. tag .. "==")
	for _, l in ipairs(lines) do
		print(l)
	end
	print("==END" .. tag .. "==")
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
print("[*] listo — copia TODO el bloque de arriba y pásamelo")
'''

rec = (TEMPLATE.replace('__QUERIES__', qlines)
               .replace('__POS__', fpos.group(1) if fpos else 'UDim2.new(0, 0, 0, 0)')
               .replace('__SIZE__', fsize.group(1) if fsize else 'UDim2.new(0, 216, 0, 178)')
               .replace('__CPS__', control_points))
open(OUT, 'w', encoding='utf-8', newline='\n').write(rec)
print("[+] wrote %s (%d queries)" % (OUT, len(queries)))
