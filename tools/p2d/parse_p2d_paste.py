"""Convierte el pegote del grabador Path2D (==P2D== ... ==END==) en el cache
<path2d> que el motor usa para repetir las respuestas reales.

Uso:
  python3 scripts/parse_p2d_paste.py <archivo_con_el_pegote> [--out <script>.path2d] [--dry]
  (o pega el bloque en un archivo y pásalo; también acepta el pegote por stdin)

Por defecto escribe samples/deobf_pls.path2d (script v15). Para el Cokeboys
v14.8 usa: --out samples/cokeboys_v148.path2d
"""
import re
import sys

OUT = "samples/deobf_pls.path2d"
MIN_ENTRIES = 11
KEY_RE = re.compile(r"^(Get(?:Position|Tangent|Length|MaxControlPoints|ControlPoints|BoundingRect)\w*)"
                    r"(?:\|(-?[\d.]+(?:[eE][-+]?\d+)?))?")


def main():
    dry = "--dry" in sys.argv
    out = OUT
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out") + 1]
    files = [a for a in sys.argv[1:] if not a.startswith("--") and a != out]
    text = ""
    if files:
        text = open(files[0], encoding="utf-8", errors="replace").read()
    else:
        text = sys.stdin.read()

    # solo el primer bloque ==P2D...== (la réplica exacta; las variantes
    # GUI/WS son solo diagnóstico)
    m = re.search(r"==P2D==(.*?)==END==", text, re.S)
    if not m:
        sys.exit("[!] no encontré el bloque ==P2D== ... ==END== en el pegote")
    block = m.group(1)

    entries = {}
    errors = []
    for line in block.splitlines():
        line = line.strip()
        if not line or line.startswith("--") or line.startswith("["):
            continue
        # el tab puede haberse perdido al copiar: separador tab o 2+ espacios
        parts = re.split(r"\t|\s{2,}", line, 1)
        if len(parts) != 2:
            continue
        key, val = parts[0].strip(), parts[1].strip()
        if not KEY_RE.match(key):
            continue
        if "ERROR" in val:
            errors.append((key, val))
            continue
        if not re.match(r"^[nzuv]:", val):
            continue
        entries[key] = val

    print("entradas válidas: %d" % len(entries))
    for k, v in entries.items():
        print("  %-45s %s" % (k, v))
    if errors:
        print("con ERROR (revisar):")
        for k, v in errors:
            print("  %-45s %s" % (k, v[:80]))
    if len(entries) < MIN_ENTRIES:
        print("[!] faltan entradas (esperaba >= %d); revisa el pegote" % MIN_ENTRIES)
    if dry or not entries:
        return
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("".join("%s\t%s\n" % kv for kv in entries.items()))
    print("[+] escrito: %s" % out)


if __name__ == "__main__":
    main()
