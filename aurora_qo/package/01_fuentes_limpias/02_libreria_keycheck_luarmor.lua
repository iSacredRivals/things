local a
local b = getfenv()["This is the key check library used by Luarmor, documentation can be viewed at https://docs.luarmor.net/luarmor-user-manual-and-f.a.q#key-check-library"]
do
  local function c(d)
    return d % 4294967296
  end
  local function e(f, g)
    local h, i = 0, 1
    while (f > 0) or (g > 0) do
      local j = f % 2
      local k = g % 2
      if j ~= k then
        h = h + i
      end
      f = math.floor(f / 2)
      g = math.floor(g / 2)
      i = i * 2
    end
    return h
  end
  local function l(d, m)
    return c(d * (2 ^ m))
  end
  local function n(d, m)
    return math.floor(d / (2 ^ m)) % 4294967296
  end
  function a(o)
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
end
local G
local H = game:GetService("HttpService")
local function I(J)
  return H:JSONDecode(J)
end
local K = ((syn and syn.request) or request) or http_request
local function L(M)
  local N = os.time()
  M = tostring(M)
  G = tostring(G)
  local O = K({Method = "GET", Url = "https://sdkapi-public.luarmor.net/sync"})
  O = I(O.Body)
  local P = O.nodes
  local Q = P[math.random(1, #P)]
  local R = Q .. ("check_key?key=" .. (M .. ("&scr" .. ("ipt_id=" .. G))))
  local S = O.st
  local T = S - N
  N = N + T
  O = K({Method = "GET", Url = R, Headers = {["clienttime"] = "" .. N, ["catcat128"] = a(M .. ("_cfver1.0_" .. (G .. ("_time_" .. N))))}})
  return I(O.Body)
end
local function U()
  G = tostring(G)
  if not G:match("^[a-f0-9]{32}$") then
    return
  end
  pcall(writefile, G .. "-cache.lua", "recache is required")
  wait(0.1)
  pcall(delfile, G .. "-cache.lua")
end
local function V()
  loadstring(game:HttpGet("https:" .. ("//ap" .. ("" .. ("i.luarmo" .. ("r.ne" .. ("t/file" .. ("s/v3/l" .. ("oaders/" .. (tostring(G) .. ".lua"))))))))))()
end
return setmetatable({}, {__index = function(W, X)
  local Y = a(X)
  if Y == "30F75B193B948B4E965146365A85CBCC" then
    return L
  end
  if Y == "2BCEA36EB24E250BBAB188C73A74DF10" then
    return U
  end
  if Y == "75624F56542822D214B1FE25E8798CC6" then
    return V
  end
  return nil
end, __newindex = function(W, Z, _)
  if Z == "script_id" then
    G = _
  end
end})