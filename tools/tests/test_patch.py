import sys, os
sys.path.insert(0, "deobf")
import harness
from obfuscators.luraph_v15 import vmmap
from obfuscators.luraph_v15.driver import patch_entries

path = "samples/deobf_pls.lua"
src = open(path, encoding="latin-1", newline="").read()
print("[*] fuente:", len(src), "chars")

root = vmmap.load_ast(path)
print("[*] AST cargado:", type(root).__name__)

closures = list(vmmap.closure_entries(root))
print("[*] closures encontrados:", len(closures))
for l1, c1, pv in closures[:5]:
    print("   proto", pv, "en linea", l1, "col", c1)

makers = list(vmmap.maker_info(root))
print("[*] makers encontrados:", len(makers))

patched = patch_entries(src, path)
print("[*] parcheado:", len(patched), "chars")
print("[*] contiene __PID:", "__PID" in patched)
print("[*] ocurrencias __PID:", patched.count("__PID"))
