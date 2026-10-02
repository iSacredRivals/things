#!/usr/bin/env python3
"""Aplica los valores Path2D reales (del user) al MITM harness y lo relanza.
Uso: python3 apply_p2d.py <archivo-con-las-12-lineas>
(tambien intenta bajarlos del bin filebin qopremium-delta-03 si no se pasa archivo)
"""
import sys, os, re, time, subprocess

HERE = "/home/z/my-project/deobf/aurora"
MITM_DIR = HERE + "/analysis/replay/mitm"

P2D_LINES_RE = re.compile(r"^(?:Get(?:Position|Tangent)\w*\|[^=\s\t]+\t[nuv]:.+|GetLength\tn:.+)$", re.M)

def parse_p2d_text(text):
    entries = {}
    for m in P2D_LINES_RE.finditer(text):
        line = m.group(0).strip()
        key, _, val = line.partition("\t")
        entries[key] = val.strip()
    return entries

def collect():
    # 1) archivo pasado como arg
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        return parse_p2d_text(open(sys.argv[1], encoding="latin-1").read())
    # 2) bajar del filebin
    import urllib.request
    try:
        with urllib.request.urlopen("https://filebin.net/qopremium-delta-03", timeout=20) as r:
            html = r.read().decode("utf-8", "replace")
        names = set(re.findall(r"(path2d_\d+\.txt)", html))
        print(f"[bin] archivos: {sorted(names)}")
        for n in sorted(names, reverse=True):
            url = f"https://filebin.net/qopremium-delta-03/{n}"
            req = urllib.request.Request(url, headers={"User-Agent": "luau"})
            try:
                with urllib.request.urlopen(req, timeout=20) as r:
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

def main():
    entries = collect()
    if not entries or len(entries) < 12:
        print(f"[!] no encontre las 12 lineas ({len(entries) if entries else 0})")
        sys.exit(1)
    print(f"[+] {len(entries)} valores Path2D reales:")
    for k, v in sorted(entries.items()):
        print(f"    {k} -> {v}")

    # escribir el cache .path2d (harness lo lee via load_p2d_cache)
    p2d_file = HERE + "/analysis/replay/mitm/obf_4.path2d"
    with open(p2d_file, "w", encoding="latin-1", newline="\n") as f:
        for k, v in entries.items():
            f.write(f"{k}\t{v}\n")
    print(f"[+] cache: {p2d_file}")

    # reconstruir el harness con el cache (make_mitm lee P2D_CACHE del archivo)
    sys.path.insert(0, "/home/z/my-project/deobf/deobf")
    os.chdir("/home/z/my-project/deobf/deobf")
    import harness as H
    H.P2D_CACHE.update(entries)
    # reinyectar en make_mitm
    src = open(HERE + "/scripts/make_mitm.py").read()
    inject = "H.P2D_CACHE.update(" + repr(entries) + ")\n"
    anchor = "# ---------- 2) chunks parcheados (VMC) ----------"
    if "H.P2D_CACHE.update" not in src:
        src = src.replace(anchor, inject + "\n" + anchor)
        open(HERE + "/scripts/make_mitm.py", "w").write(src)
        print("[+] make_mitm.py actualizado con el cache real")

    r = subprocess.run([sys.executable, HERE + "/scripts/make_mitm.py"],
                       capture_output=True, text=True, timeout=180)
    print(r.stdout[-1500:])
    if r.returncode != 0:
        print(r.stderr[-1500:])
        sys.exit(1)

    # relanzar harness + driver
    subprocess.call(f"pkill -f mitm_harness.luau; pkill -f mitm_driver.py; sleep 1", shell=True)
    for f in os.listdir(MITM_DIR):
        if f.startswith("resp_"):
            os.remove(os.path.join(MITM_DIR, f))
    log = open(MITM_DIR + "/mitm_harness.log", "w")
    drv = open(MITM_DIR + "/driver_console.log", "w")
    subprocess.Popen(["/home/z/my-project/deobf/deobf/bin/luau", "mitm_harness.luau"],
                     cwd=MITM_DIR, stdout=log, stderr=subprocess.STDOUT,
                     start_new_session=True)
    time.sleep(2)
    subprocess.Popen([sys.executable, HERE + "/scripts/mitm_driver.py"],
                     cwd=MITM_DIR, stdout=drv, stderr=subprocess.STDOUT,
                     start_new_session=True)
    print("[+] relanzado: harness + driver (nohup)")
    print("    mira: analysis/replay/mitm/mitm_harness.log")

if __name__ == "__main__":
    main()
