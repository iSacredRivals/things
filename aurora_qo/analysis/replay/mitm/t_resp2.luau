local ok, r = pcall(function() return require("./resp_2") end)
print("ok:", ok, "type:", type(r))
if type(r) == "table" then
    print("body len:", #r.__body, "code:", r.__code)
    print("body start:", r.__body:sub(1, 60))
elseif type(r) == "string" then
    print("STRING RESULT:", r:sub(1, 150))
end
