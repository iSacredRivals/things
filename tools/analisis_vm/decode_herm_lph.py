#!/usr/bin/env python3
"""Decode the LPH ASCII85 blob of hermanos_v145.lua (v14.5.2).

The runtime decoder (from the source):
  local p,X,x,n,R = string.byte(m,1,5)
  z = (R-0x21) + (n-0x21)*85 + (x-0x21)*7225 + (X-0x21)*614125 + (p-0x21)*52200625
  replacement = string.pack(">I4", z)
So each 5-char group -> one big-endian u32 -> 4 bytes.
"""
import re
import struct

SRC = "samples/hermanos_v145.lua"

src = open(SRC, encoding="latin-1").read()
m = re.search(r"\[(=+)\[LPH(.*?)\]\1\]", src, re.S)
blob = m.group(2)
print(f"blob: {len(blob)} chars")

# decode in 5-char groups
out = bytearray()
skipped = 0
for i in range(0, len(blob), 5):
    g = blob[i:i+5]
    if len(g) < 5:
        skipped += 1
        continue
    z = 0
    for ch in g:
        z = z * 85 + (ord(ch) - 0x21)
    out += struct.pack(">I", z & 0xFFFFFFFF)
print(f"decoded: {len(out)} bytes ({skipped} short groups skipped)")

# stats
from collections import Counter
c = Counter(out)
print("top bytes:", c.most_common(8))
nz = sum(1 for b in out if b != 0)
print(f"non-zero bytes: {nz} ({100*nz/len(out):.1f}%)")

# look for readable ascii runs (>=6)
runs = []
cur = b""
for b in out:
    if 32 <= b < 127:
        cur += bytes([b])
    else:
        if len(cur) >= 6:
            runs.append(cur.decode())
        cur = b""
if len(cur) >= 6:
    runs.append(cur.decode())
print(f"ascii runs >=6: {len(runs)}")
for r in runs[:30]:
    print("   ", r[:100])

open("/tmp/herm_lph.bin", "wb").write(out)
print("saved /tmp/herm_lph.bin")

# u32 view
words = struct.unpack(">%dI" % (len(out)//4), out[:len(out)//4*4])
print("first 32 words (BE u32):", [hex(w) for w in words[:32]])
