#!/usr/bin/env python3
"""Drivers para la desofuscación de los archivos Luarmor de DevAurora-Scripts.

Uso:
  python3 aurora_drivers.py prelude4    # genera prelude_obf4.luau (_bsdata0)
  python3 aurora_drivers.py patch4      # genera obf_4_arg.lua (:TK()("f07dbcbe19a-sephal"))
"""
import re
import sys
import os

BASE = "/home/z/my-project/deobf/aurora"
EXTR = os.path.join(BASE, "extracted")
GEN = os.path.join(BASE, "analysis")

# ---- extraer _bsdata0 del stub obf_3.lua ------------------------------------
def extract_bsdata(stub_path):
    src = open(stub_path, encoding="utf-8", errors="replace").read()
    m = re.search(r"_bsdata0\s*=\s*(\{.*?\});", src, re.S)
    if not m:
        raise SystemExit("no _bsdata0 en " + stub_path)
    return m.group(1)

def gen_prelude4():
    tbl = extract_bsdata(os.path.join(EXTR, "obf_3.lua"))
    code = (
        "-- prelude: globals que el stub Luarmor deja antes de cargar el bootstrapper\n"
        "rawset(G, \"_bsdata0\", " + tbl + ")\n"
        "rawset(G, \"ldrupd8m\", nil)\n"
    )
    out = os.path.join(GEN, "prelude_obf4.luau")
    open(out, "w", encoding="utf-8").write(code)
    print("[+] prelude:", out, len(code), "bytes")

def gen_patch4():
    src = open(os.path.join(EXTR, "obf_4.lua"), encoding="utf-8", errors="replace").read()
    # el stub real llama loadstring(v4_init)("f07dbcbe19a-sephal"): parcheamos la
    # invocación final :TK()(...) -> :TK()("f07dbcbe19a-sephal") (misma 1 línea)
    needle = ":TK()(...)"
    assert needle in src, "no encuentro :TK()(...) en obf_4"
    patched = src.replace(needle, ':TK()("f07dbcbe19a-sephal")', 1)
    out = os.path.join(GEN, "obf_4_arg.lua")
    open(out, "w", encoding="utf-8").write(patched)
    print("[+] patched:", out, len(patched), "bytes")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "prelude4":
        gen_prelude4()
    elif cmd == "patch4":
        gen_patch4()
    else:
        print(__doc__)
