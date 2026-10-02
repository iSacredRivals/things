local d = 0
local function f() d += 1; return 1 + f() end
local ok, err = pcall(f)
print("pure recursion:", err)
local function g(n) local ok2, err2 = pcall(g, n + 1) return ok2 and 0 or 0 end
local ok3, err3 = pcall(function() return g(0) end)
print("pcall chain:", err3)
