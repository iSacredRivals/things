-- Diagnóstico de pila: qué hay en cada nivel cuando el VM consulta debug.info(n, ...)
-- El prelude corre ANTES del script y ANTES del table.freeze de las librerías,
-- así que puede reemplazar debug.info por una versión que registra y pasa a través.
local E = env
local dbg = E.debug
local __di = dbg.info
local tostring = E.tostring
local type = E.type
local seen = {}
dbg.info = function(a, b, c)
	if type(a) == "number" then
		local src = __di(a, "s")
		local nm = __di(a, "n")
		local ln = __di(a, "l")
		local key = tostring(a) .. "|" .. tostring(src) .. "|" .. tostring(nm) .. "|" .. tostring(ln)
		if not seen[key] then
			seen[key] = true
			E.print("[LVL] lvl=" .. tostring(a) .. " what=" .. tostring(b)
				.. " src=" .. tostring(src) .. " name=" .. tostring(nm)
				.. " line=" .. tostring(ln))
		end
	end
	return __di(a, b, c)
end
