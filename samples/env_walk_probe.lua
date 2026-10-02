-- probe: enumerate getfenv() exactly like the hermanos VM does
local keys = {}
local n = 0
for k, v in pairs(getfenv()) do
    n = n + 1
    keys[n] = k
end
table.sort(keys)
print("ENV pairs count:", n)
print("keys:", table.concat(keys, " "))
local e = getfenv()
print("rawget print:", type(rawget(e, "print")))
print("rawget string:", type(rawget(e, "string")))
print("rawget task:", type(rawget(e, "task")))
print("rawget os:", type(rawget(e, "os")))
print("rawget getgenv:", type(rawget(e, "getgenv")))
print("rawget shared:", type(rawget(e, "shared")))
print("type(script)=", type(script))
print("debug.info(1,'s')=", debug.info(1, "s"))
