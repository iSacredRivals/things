-- Primitivas de debug.info en bin/luau: qué devuelve con funciones vs niveles
local function foo(a, b, ...)
	return a
end

local function caller()
	print("fn s:", debug.info(foo, "s"))
	print("fn l:", debug.info(foo, "l"))
	print("fn n:", debug.info(foo, "n"))
	print("fn a:", debug.info(foo, "a"))
	print("fn f==foo:", debug.info(foo, "f") == foo)
	print("fn slnaf:", debug.info(foo, "slnaf"))
	print("lvl1 s:", debug.info(1, "s"))
	print("lvl1 l:", debug.info(1, "l"))
	print("lvl1 n:", debug.info(1, "n"))
	print("lvl2 s:", debug.info(2, "s"))
	print("lvl3 s:", debug.info(3, "s"))
	print("lvl9 s (out of range):", debug.info(9, "s"))
	print("C s:", debug.info(print, "s"))
	print("C l:", debug.info(print, "l"))
	print("C a:", debug.info(print, "a"))
	print("C slnaf:", debug.info(print, "slnaf"))
	print("main s:", debug.info(1, "s"), "(desde caller, lvl1=caller)")
end
caller()
print("chunk s:", debug.info(1, "s"))
