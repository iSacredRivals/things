-- Test vectors del hash catcat128 extraído de obf_2_clean.lua (SDK Luarmor)
-- Se ejecuta con luau (semántica de doubles = la del executor)
local function c(d) return d % 4294967296 end
local function e(f, g)
	local h, i = 0, 1
	while (f > 0) or (g > 0) do
		local j = f % 2
		local k = g % 2
		if j ~= k then h = h + i end
		f = math.floor(f / 2)
		g = math.floor(g / 2)
		i = i * 2
	end
	return h
end
local function l(d, m) return c(d * (2 ^ m)) end
local function n(d, m) return math.floor(d / (2 ^ m)) % 4294967296 end
local function a(o)
	local p = {[1] = 1524013928, [2] = 62333482, [3] = 755453430, [4] = 3411017517}
	local q = {[1] = 451, [2] = 41992, [3] = 38477, [4] = 17184}
	local r = #o
	local s = 1
	while s <= r do
		local t = 0
		for u = 0, 3 do
			local v = (s - 1) + u
			if v < r then
				local w = o:byte(v + 1)
				t = t + (w * (2 ^ (8 * u)))
			end
		end
		t = c(t)
		for x = 1, 4 do
			local y = e(p[x], t)
			local z = p[(x % 4) + 1]
			y = e(y, z)
			y = c((l(y, 5) + n(y, 2)) + q[x])
			local A = ((x - 1) * 5) % 32
			local B = n(t, A)
			y = e(y, B)
			y = c(y)
			local C = p[((x + 1) % 4) + 1]
			y = c(y + C)
			p[x] = c(y)
		end
		s = s + 4
	end
	for x = 1, 4 do
		local y = p[x]
		local D = p[(x % 4) + 1]
		local E = p[((x + 2) % 4) + 1]
		y = c(y + D)
		y = e(y, E)
		local A = (x * 7) % 32
		y = c(l(y, A) + n(y, 32 - A))
		p[x] = y
	end
	local F = {}
	for x = 1, 4 do
		F[x] = string.format("%08X", p[x])
	end
	return table.concat(F)
end

local inputs = {
	"test",
	"abcdefgh12345678",
	string.rep("x", 100),
	"LbdcJNWbjhlelJHknRFNRcbBzibDAyTl_cfver1.0_0ae9fe4cf963e3a13d25eed0e2ce5940_time_1759190000",
	"KEY_cfver1.0_0123456789abcdef0123456789abcdef_time_1",
	"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa_cfver1.0_0ae9fe4cf963e3a13d25eed0e2ce5940_time_9999999999",
	"z",
	"ab",
	"abc",
	"abcd",
}
for _, inp in ipairs(inputs) do
	print(a(inp))
end
