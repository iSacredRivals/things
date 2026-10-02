-- This file was protected using Luraph Obfuscator v14.8 [https://lura.ph/]
--[[
        Synthetic v14.8 guard/throttle test: a hot loop that emits per
        iteration (print) - before the engine fix this truncated the block
        at 25000 statements and the run died before reaching the code after
        the loop.
]]

local acc = 0
local i = 0
while true do
	i += 1
	acc += i
	print(i)
	if i >= 200000 then break end
end
print("loop done " .. acc)
local Players = game:GetService("Players")
print("after loop " .. tostring(Players))
