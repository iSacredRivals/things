#!/usr/bin/env python3
"""Analyze VM dispatcher structure of Luraph v15 protected scripts."""
import re, sys

def analyze(path, label):
    src = open(path, "r", encoding="utf-8", errors="replace").read()
    print(f"=== {label} ({len(src)} bytes) ===")
    # classic dispatcher: while true do op = ARR[pc]; ...
    classic = re.findall(r"while true do[\s\S]{0,400}?\[", src)
    print(f"while true do count: {src.count('while true do')}")
    # method-chained: M:Z0(L,A,j) style dispatch
    chained = re.findall(r"(\w+):(\w+)\(", src)
    from collections import Counter
    c = Counter(chained)
    print("top method-call sites (recv:method -> count):")
    for (recv, meth), n in c.most_common(8):
        print(f"   {recv}:{meth}  x{n}")
    # how many setmetatable(...)({handlers}
    print("setmetatable count:", src.count("setmetatable"))
    # LPH macros
    for macro in ("LPH_JIT", "LPH_NOVIRTUALIZE", "LPH_ENCSTR", "LPH_ENCBUF", "LPH_PRECHECK"):
        n = src.count(macro)
        if n: print(f"{macro}: {n}")
    # return signature style: handlers return op codes (numbers) -> tail dispatch
    print("return patterns like 'return N,...':", len(re.findall(r"return \d+,", src)))
    print()

analyze("/home/z/my-project/luarmor_task/anhdomixi_raw.lua", "anhdomixi")
analyze("/home/z/my-project/luarmor_task/kaitun_raw.lua", "kaitun")
