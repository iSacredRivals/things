-- Test del mecanismo prelude: se ejecuta? se puede mutar debug? print funciona?
local E = env
local ok1, err1 = E.pcall(function() E.debug.info = E.debug.info end)
E.print("[PRE] exec_ok freeze_test=" .. E.tostring(ok1) .. " err=" .. E.tostring(err1))
local ok2, err2 = E.pcall(function()
	local dbg = E.debug
	local __di = dbg.info
	dbg.info = function(a, b, c)
		if E.type(a) == "number" then
			E.print("[LVL] lvl=" .. E.tostring(a) .. " what=" .. E.tostring(b))
		end
		return __di(a, b, c)
	end
end)
E.print("[PRE] patch_test ok=" .. E.tostring(ok2) .. " err=" .. E.tostring(err2))
