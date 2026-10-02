#!/usr/bin/env bash
# Compila luau + luau-ast (Luau 0.739) con el parche del vector metatable,
# ajustado a ESTA máquina: 2 núcleos / 3.9 GB → sin LTO y -j2 para no morir de OOM.
set -euo pipefail
cd "$(dirname "$0")/.."   # project root

SRC=scripts/luau-src
BD="$SRC/build-deobf"
BIN=deobf/deobf/bin

# 1) parche del metatable de vector (idéntico al de deobf/build_luau.py)
python3 - "$SRC/VM/src/lveclib.cpp" <<'PY'
import sys
path = sys.argv[1]
FREEZE = "    lua_setreadonly(L, -1, true);\n    lua_pop(L, 1); // pop the metatable\n"
PATCHED = "    // deobf: left writable, envlog.luau adds Roblox's Vector3 members\n    lua_pop(L, 1); // pop the metatable\n"
text = open(path, encoding="utf-8").read()
if PATCHED not in text:
    assert text.count(FREEZE) == 1, "lveclib.cpp cambió upstream: parchear a mano"
    open(path, "w", encoding="utf-8", newline="\n").write(text.replace(FREEZE, PATCHED))
    print("[+] parche aplicado")
PY

# 2) configure (Release, sin LTO)
if [ ! -f "$BD/CMakeCache.txt" ]; then
  cmake -S "$SRC" -B "$BD" -DCMAKE_BUILD_TYPE=Release \
        -DLUAU_BUILD_TESTS=OFF -DLUAU_STATIC_CRT=ON \
        -DCMAKE_C_COMPILER=gcc -DCMAKE_CXX_COMPILER=g++ \
        -DCMAKE_C_FLAGS_RELEASE="-O2 -DNDEBUG" \
        -DCMAKE_CXX_FLAGS_RELEASE="-O2 -DNDEBUG" \
        -DCMAKE_EXE_LINKER_FLAGS="-static" > /dev/null
  echo "[+] cmake configurado"
fi

# 3) ambos targets, -j2
cmake --build "$BD" --config Release --target Luau.Repl.CLI --parallel 2
cmake --build "$BD" --config Release --target Luau.Ast.CLI --parallel 2

mkdir -p "$BIN"
for name in luau luau-ast; do
  for cand in "$BD/Release/$name" "$BD/$name"; do
    if [ -f "$cand" ]; then cp -f "$cand" "$BIN/$name"; echo "[+] wrote $BIN/$name"; break; fi
  done
done
echo "[✔] build completo"
