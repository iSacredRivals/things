#!/usr/bin/env python3
"""Analyze [call]/-> nesting in an envlog ptrace raw output: find the
recursion cycle that overflows the C stack."""
import re
import sys

raw_path = sys.argv[1] if len(sys.argv) > 1 else "samples/output/hermanos_raw3.txt"
raw = open(raw_path, encoding="utf-8", errors="replace").read()
lines = raw.split("\n")

depth = 0
max_depth = 0
stack = []
events = []  # (index, depth, label)
for i, l in enumerate(lines):
    if l.startswith("[call]\t"):
        rest = l[len("[call]\t"):]
        label = rest.split("(")[0]
        # two [call] formats: traceWrap "[call] label(args)" and onCall ptrace
        # "[call] name n arg" (name is a bare word, no parens; fields split by tab)
        fields = l.split("\t")
        if "(" not in fields[1] and len(fields) >= 4:
            continue  # onCall ptrace line: no matching '->' pair
        depth += 1
        stack.append(label)
        if depth > max_depth:
            max_depth = depth
        events.append((i, depth, label))
    elif l.startswith("   ->\t"):
        if stack:
            stack.pop()
        depth -= 1

print(f"max tracked depth: {max_depth}, final depth: {depth}")

# find the deepest point and print the stack there
peak = max(events, key=lambda e: e[1])
print(f"deepest call at line {peak[0]}: {peak[2]}")
# reconstruct the stack at that point: walk events up to peak
st = []
for i, d, label in events:
    if i > peak[0]:
        break
    while st and len(st) >= d:
        st.pop()
    st.append(label)
print(f"stack at deepest point ({len(st)} frames):")
# compress: show the cycle pattern
from collections import Counter
c = Counter(st)
print("top frame types:", c.most_common(12))
# find the repeating cycle in the tail of the stack
if len(st) > 20:
    print("tail 30 frames:", st[-30:])
