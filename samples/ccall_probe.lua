local function f(n) return 1 + f(n + 1) end
local ok, err = pcall(f, 0)
print("recursion depth error:", err)
