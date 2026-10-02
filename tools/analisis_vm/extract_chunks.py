#!/usr/bin/env python3
"""Extract \0CHUNK hex payloads from a raw envlog output into .lua files."""
import re, sys

raw = open(sys.argv[1], encoding="utf-8", errors="replace").read()
out_prefix = sys.argv[2] if len(sys.argv) > 2 else "chunk"

found = re.findall(r"\x00CHUNK (\S+)\n([0-9a-f]*)\n", raw)
if not found:
    print("[!] no CHUNK markers found"); sys.exit(0)

for i, (key, hx) in enumerate(found):
    src = bytes.fromhex(hx).decode("latin-1")
    name = f"{out_prefix}_{i}_{key}.lua"
    with open(name, "w", encoding="latin-1", newline="\n") as f:
        f.write(src)
    print(f"[+] {name}: {len(src)} bytes")
