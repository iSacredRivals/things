print("Random global:", Random)
if Random then
	print("new(0):NextNumber =", Random.new(0):NextNumber())
	print("new(0) seq 2-5 =", Random.new(0):NextNumber(), Random.new(0):NextNumber())
	local r = Random.new(42)
	print("new(42) 3 valores =", r:NextNumber(), r:NextNumber(), r:NextNumber())
	print("NextInteger(1,100) =", r:NextInteger(1, 100))
	print("NextUnitVector =", r:NextUnitVector())
	print("type:", typeof(Random), typeof(Random.new(0)))
end
