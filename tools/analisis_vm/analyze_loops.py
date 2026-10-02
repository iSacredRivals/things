"""Analyze all while-true loops in the protected script: classify dispatch forms.

Runs luau-ast on the file, walks every AstStatWhile with constant-true
condition, and prints the shape of its first statements so we can see which
forms the engine's find_dispatchers would need to recognize.
"""
import json
import subprocess
import sys

ROOT = "samples"
path = sys.argv[1] if len(sys.argv) > 1 else ROOT + "/samples/deobf_pls.lua"

exe = ROOT + "/deobf/bin/luau-ast"
r = subprocess.run([exe, path], capture_output=True)
if r.returncode != 0:
    sys.exit("parse failed: %s" % r.stderr.decode("latin-1")[:500])
root = json.loads(r.stdout.decode("latin-1"))["root"]

with open(path, encoding="latin-1") as f:
    src = f.read()
lines = src.split("\n")


def loc(node):
    a, b = node["location"].split(" - ")
    l1, c1 = map(int, a.split(","))
    return l1, c1


def text_of(node):
    l1, c1, l2, c2 = (lambda a, b: (a[0], a[1], b[0], b[1]))(
        *map(lambda x: tuple(map(int, x.split(","))), node["location"].split(" - ")))
    if l1 == l2:
        return lines[l1][c1:c2]
    parts = [lines[l1][c1:]] + lines[l1 + 1:l2] + [lines[l2][:c2]]
    return "\n".join(parts)


def local_name(expr):
    if expr.get("type") == "AstExprLocal":
        return expr["local"]["name"]
    return None


def walk(node, fn):
    if isinstance(node, dict):
        fn(node)
        for v in node.values():
            walk(v, fn)
    elif isinstance(node, list):
        for v in node:
            walk(v, fn)


loops = []


def visit(n):
    if n.get("type") != "AstStatWhile":
        return
    cond = n["condition"]
    if cond.get("type") != "AstExprConstantBool" or not cond.get("value"):
        return
    body = n["body"]["body"]
    if not body:
        return
    head = text_of(body[0])[:100].replace("\n", " ")
    loops.append((n, body, head))


walk(root, visit)
print("total while-true loops:", len(loops))

# classify: which loops have an if as body[0]? which have local x = ARR[PC]?
classic = 0
if_first = 0
other = 0
for n, body, head in loops:
    t = body[0]["type"]
    if t == "AstStatIf":
        if_first += 1
    elif t in ("AstStatLocal", "AstStatAssign") and len(body) > 1 and body[1]["type"] == "AstStatIf":
        # check the classic form: single value, index expr
        st = body[0]
        vals = st.get("values", [])
        if len(vals) == 1 and vals[0].get("type") == "AstExprIndexExpr":
            classic += 1
        else:
            other += 1
    else:
        other += 1

print("classic-shaped (local op=ARR[PC]; if...):", classic)
print("if-first (opcode var threaded):", if_first)
print("other:", other)

print()
print("=== if-first loops (first 40) ===")
shown = 0
for n, body, head in loops:
    if body[0]["type"] != "AstStatIf":
        continue
    cond = body[0]["condition"]
    ct = text_of(cond)[:60].replace("\n", " ")
    nstmt = len(body)
    print("loc=%s cond=[%s] stmts=%d head=%s" % (n["location"], ct, nstmt, head[:70]))
    shown += 1
    if shown >= 40:
        break
