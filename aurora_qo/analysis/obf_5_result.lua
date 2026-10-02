-- Deobfuscated by ccjvwsod on Discord
-- Detected obfuscation: Luraph v14.8
-- Deobfuscated by deobf (dynamic trace)
-- source: obf_5.lua
-- NOTE: reconstructed from observed behaviour; branches that were not taken
--       during the trace are missing and conditions are only noted in comments.
-- run status: stopped in an endless loop (truncated)
-- 165 statements recorded in 0.96s
-- non-standard globals touched: ce_like_loadstring_fn, UserSettings, devsignature_sig, LUARMOR_SkipAntidebugDevMode, LUARMOR_AllowKeyCheckSkip, USE_NON_SSL_NODE, l_fastload_enabled, script_key, syn, FLUXUS_LOADED

-- [deobf] folded 0 repeated calls into 0 helper functions and 1 unrolled runs into loops
-- [deobf] removed 55 lines of the obfuscator's environment/anti-tamper probes
local RunService = game:GetService("RunService")
local result = UserSettings()
local UserGameSettings = result:GetService("UserGameSettings")

for _, text in ipairs({
	"nil  nil  ", "nil  nil  0", "nil  nil  1", "nil  nil  2", "nil  nil  3", "nil  nil  4",
	"nil  nil  5", "nil  nil  6", "nil  nil  7", "nil  nil  8", "nil  nil  9", "nil  nil  10",
	"nil  nil  11", "nil  nil  12", "nil  nil  13", "nil  nil  14", "nil  nil  15", "nil  nil  16",
	"nil  nil  17", "nil  nil  18", "nil  nil  19", "nil  nil  20", "nil  nil  21", "nil  nil  22",
	"nil  nil  23", "nil  nil  24", "nil  nil  25", "nil  nil  26", "nil  nil  27", "nil  nil  28",
	"nil  nil  29", "nil  nil  30", "nil  nil  31", "nil  nil  32", "nil  nil  33", "nil  nil  34",
	"nil  nil  35", "nil  nil  36", "nil  nil  37", "nil  nil  38", "nil  nil  39", "nil  nil  40",
	"nil  nil  41", "nil  nil  42", "nil  nil  43", "nil  nil  44", "nil  nil  45", "nil  nil  46",
	"nil  nil  47", "nil  nil  48", "nil  nil  49", "nil  nil  50", "nil  nil  51", "nil  nil  52",
	"nil  nil  53", "nil  nil  54", "nil  nil  55", "nil  nil  56", "nil  nil  57", "nil  nil  58",
	"nil  nil  59", "nil  nil  60", "nil  nil  61", "nil  nil  62", "nil  nil  63", "nil  nil  64",
	"nil  nil  65", "nil  nil  66", "nil  nil  67", "nil  nil  68", "nil  nil  69", "nil  nil  70",
	"nil  nil  71", "nil  nil  72", "nil  nil  73", "nil  nil  74", "nil  nil  75", "nil  nil  76",
	"nil  nil  77", "nil  nil  78", "nil  nil  79",
}) do
	UserGameSettings:GetTutorialState(text)
end

print("        Luarmor - Lua whitelist service\n        This is a signature - If you are seeing this, you know what not to do :3\n        Have a good day!\n        https://luarmor.net/\n    ")
local LocalizationService = game:GetService("LocalizationService")
local Players = game:GetService("Players")
LocalizationService:GetCountryRegionForPlayerAsync(Players.LocalPlayer)

spawn(function()
	RunService.Heartbeat:Wait()
	RunService.Heartbeat:Wait()
	-- [envlog] the statements above repeat forever (loop)
end)

-- identifyexecutor() -> "Wave"
-- identifyexecutor() -> "Wave"
-- identifyexecutor() -> "Wave"
print(772873)

spawn(function()
	local children = game.CoreGui.DevConsoleMaster.DevConsoleWindow.DevConsoleUI.MainView.ClientLog:GetChildren()

	for k, v in pairs(children) do
		v:FindFirstChild("msg")
		v.msg.Text:sub(3)
	end

	wait(0.05)
	local children2 = game.CoreGui.DevConsoleMaster.DevConsoleWindow.DevConsoleUI.MainView.ClientLog:GetChildren()

	for k2, v2 in pairs(children2) do
		v2:FindFirstChild("msg")
		v2.msg.Text:sub(3)
	end

	wait(0.05)
	-- [envlog] the statements above repeat forever (loop)
end)

spawn(function()
	wait(0.03)
	wait(0.03)
	-- [envlog] the statements above repeat forever (loop)
end)

RunService.Heartbeat:Wait()
RunService.Heartbeat:Wait()
-- [envlog] the statements above repeat forever (loop)
