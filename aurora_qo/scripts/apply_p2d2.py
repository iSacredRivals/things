#!/usr/bin/env python3
"""Aplica los valores Path2D del LOADER (probe2 del user) al harness MITM.
Uso: python3 apply_p2d2.py <archivo-con-las-lineas>
(tambien baja del bin filebin qopremium-delta-05 si no se pasa archivo)
"""
import sys, os, re, time, subprocess

HERE = "/home/z/my-project/deobf/aurora"
MITM_DIR = HERE + "/analysis/replay/mitm"

# [\t ]+ : acepta tabs OR espacios (texto pegado del chat pierde los tabs)
P2D_LINES_RE = re.compile(r"^(?:Get(?:Position|Tangent)\w*\|[^=\s\t]+[\t ]+[nuv]:.+|GetLength[\t ]+n:.+)$", re.M)

def parse_p2d_text(text):
    entries = {}
    for m in P2D_LINES_RE.finditer(text):
        line = m.group(0).strip()
        parts = re.split(r"[\t ]+", line, 1)
        if len(parts) == 2:
            entries[parts[0]] = parts[1].strip()
    return entries

def collect():
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        return parse_p2d_text(open(sys.argv[1], encoding="latin-1").read())
    import urllib.request
    try:
        with urllib.request.urlopen("https://filebin.net/qopremium-delta-05", timeout=20) as r:
            html = r.read().decode("utf-8", "replace")
        names = set(re.findall(r"(path2d2_\d+\.txt)", html))
        print(f"[bin] archivos: {sorted(names)}")
        for n in sorted(names, reverse=True):
            url = f"https://filebin.net/qopremium-delta-05/{n}"
            req = urllib.request.Request(url, headers={"User-Agent": "luau"})
            try:
                import http.cookiejar
                opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
                with opener.open(req, timeout=20) as r:
                    body = r.read().decode("latin-1")
                entries = parse_p2d_text(body)
                if len(entries) >= 12:
                    print(f"[bin] {n}: {len(entries)} entradas validas")
                    return entries
            except Exception as e:
                print(f"[bin] {n}: {e}")
    except Exception as e:
        print(f"[bin] error: {e}")
    return None

def lua_table_str(d):
    parts = []
    for k, v in d.items():
        parts.append("[%r] = %r" % (k, v))
    return "{" + ", ".join(parts) + "}"

def main():
    entries = collect()
    # 13 lineas pero 11 claves unicas (el loader consulta |0.5 y |0.7-arc dos veces)
    if not entries or len(entries) < 11:
        print(f"[!] no encontre las lineas del loader ({len(entries) if entries else 0})")
        sys.exit(1)
    print(f"[+] {len(entries)} valores Path2D del LOADER:")
    for k, v in sorted(entries.items()):
        print(f"    {k} -> {v}")

    # actualizar L2D_DATA en make_mitm.py
    src = open(HERE + "/scripts/make_mitm.py").read()
    m = re.search(r"L2D_DATA = \{[^}]*\}", src)
    if not m:
        print("[!] L2D_DATA no encontrado en make_mitm.py")
        sys.exit(1)
    new_data = "L2D_DATA = " + repr(entries)
    src = src[:m.start()] + new_data + src[m.end():]
    open(HERE + "/scripts/make_mitm.py", "w").write(src)
    print(f"[+] make_mitm.py L2D_DATA actualizado con {len(entries)} entradas")

    # reconstruir el harness
    r = subprocess.run([sys.executable, HERE + "/scripts/make_mitm.py"],
                       capture_output=True, text=True, timeout=300)
    print(r.stdout[-1200:])
    if r.returncode != 0:
        print(r.stderr[-1200:])
        sys.exit(1)
    print("[+] harness reconstruido. Relanzar con launch_mitm.py")

if __name__ == "__main__":
    main()
