#!/usr/bin/env python3
"""Limpiador estático para la librería key-check de Luarmor (obf_2.lua).

La ofuscación es ligera: cadenas partidas con `..`, ruido de comentarios
(`--[]`, `--[[==]]`) y espaciado roto. El flujo:
  1. parse con luau-ast (binario de la suite)
  2. plegar Concat de literales ("a".."b" -> "ab")
  3. render con un statement por línea
"""
import sys
import os

sys.path.insert(0, "/home/z/my-project/deobf/deobf")
import luauast  # noqa: E402


def fold_concat(node):
    """Recorre el AST y pliega cadenas concatenadas literales."""
    if isinstance(node, dict):
        # primero los hijos
        for k, v in node.items():
            node[k] = fold_concat(v)
        if node.get("type") == "AstExprBinary" and node.get("op") == "Concat":
            left, right = node.get("left"), node.get("right")
            if isinstance(left, dict) and isinstance(right, dict) \
                    and left.get("type") == "AstExprConstantString" \
                    and right.get("type") == "AstExprConstantString":
                merged = {
                    "type": "AstExprConstantString",
                    "location": node.get("location"),
                    "value": left.get("value", "") + right.get("value", ""),
                }
                return merged
        return node
    if isinstance(node, list):
        return [fold_concat(v) for v in node]
    return node


def main():
    inp = sys.argv[1] if len(sys.argv) > 1 else \
        "/home/z/my-project/deobf/aurora/extracted/obf_2.lua"
    out = sys.argv[2] if len(sys.argv) > 2 else \
        "/home/z/my-project/deobf/aurora/analysis/obf_2_clean.lua"
    src = open(inp, encoding="utf-8", errors="replace").read()
    ast = luauast.parse(src)
    before = src.count('..')
    ast = fold_concat(ast)
    rendered = luauast.render(ast)
    open(out, "w", encoding="utf-8").write(rendered)
    print("[+] %s -> %s (%d -> %d bytes, %d '..' restantes)"
          % (inp, out, len(src), len(rendered), rendered.count("..")))


if __name__ == "__main__":
    main()
