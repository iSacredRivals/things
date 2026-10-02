#!/usr/bin/env python3
"""Extract the __index metamethod (chained-VM dispatcher) from Luraph v15 scripts."""
import re, sys

def extract_index(path, label, out):
    src = open(path, "r", encoding="utf-8", errors="replace").read()
    print(f"=== {label} ===")
    # find __index=function(
    i = src.find("__index=function")
    if i < 0:
        i = src.find("__index = function")
    print("__index at offset:", i)
    # walk to matching end of the function: count parens from "function(" onwards
    j = src.find("(", i)
    depth = 0
    k = j
    # track "function"/"end"/"do"/"if" tokens for balance
    tokens = re.finditer(r"function\b|if\b|for\b|while\b|do\b|repeat\b|until\b|end\b|\(|\)|\[\[|\]\]", src[j:j+200000])
    bal = 0
    endpos = None
    for m in tokens:
        t = m.group(0)
        if t == "function" or t == "if" or t == "for" or t == "while" or t == "do" or t == "repeat" or t == "(" or t == "until":
            bal += 1
        elif t == "end" or t == ")" or t == "until":
            bal -= 1
            if bal == 0:
                endpos = j + m.end()
                break
    print("function ends at:", endpos, "length:", endpos - i)
    body = src[i:endpos]
    open(out, "w").write(body)
    print(f"saved {len(body)} bytes -> {out}")
    print("---- first 3000 chars ----")
    print(body[:3000])
    print("---- last 1500 chars ----")
    print(body[-1500:])

extract_index("/home/z/my-project/luarmor_task/anhdomixi_raw.lua", "anhdomixi",
              "/home/z/my-project/luarmor_task/anhdomixi_index.lua")
