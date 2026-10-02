#!/usr/bin/env python3
"""Run a raw probe script through the envlog harness (no guards, no tidy)."""
import os
import sys

ENGINE = "deobf"
sys.path.insert(0, ENGINE)
os.chdir(ENGINE)

import harness  # noqa: E402

luau = harness.find_luau()
src = open(sys.argv[1], encoding="latin-1").read()
out = sys.argv[2] if len(sys.argv) > 2 else "/tmp/probe_out.txt"
body, err = harness.run_once(luau, src, {"executor": "Wave", "flat_env": True, "probe": True}, out + ".harness.luau", 60, True)
if body is None:
    print("FAILED:", (err or "")[:2000])
else:
    print(body[:4000])
