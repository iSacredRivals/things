#!/usr/bin/env python3
"""AUTOWATCHER del stage LOADER (probe2 -> payload premium).

Fases:
  A) Poll filebin.net/qopremium-delta-05 cada 45s (sesion cookie) buscando
     path2d2_*.txt con >=12 entradas validas (los 13 valores del loader).
  B) Al llegar: apply_p2d2.py <archivo>  (L2D_DATA -> rebuild del harness)
     luego launch_mitm.py (clean: resp + logs frescos, harness + driver vivos).
  C) Monitor del mitm_harness.log: L2DSWAP, \0MITM/\0MITMDONE, State294,
     loadstring() de N bytes, y resp_N.luau NUEVOS mas alla de los 3 chunks
     del loader (= PAYLOAD premium).
  D) Al detectar payload: espera 90s (descarga completa de chunks), copia
     resp_5+.luau y el log a analysis/output/premium_capture/, y escribe
     worklog + archivo de estado.

Estado en analysis/replay/mitm/AUTOWATCH.status (para inspeccion externa).
Log propio: analysis/replay/mitm/autowatch.log
"""
import os, re, sys, time, json, subprocess, urllib.request, http.cookiejar

HERE = "/home/z/my-project/deobf/aurora"
MITM = HERE + "/analysis/replay/mitm"
OUTDIR = HERE + "/analysis/output/premium_capture"
STATUS = MITM + "/AUTOWATCH.status"
WLOG = MITM + "/autowatch.log"
BIN = "qopremium-delta-05"
POLL = 45
MAX_WAIT_H = 14          # horas max esperando al user
MONITOR_MAX_S = 3000     # 50 min de replay como maximo
PAYLOAD_GRACE_S = 90     # espera tras el primer chunk nuevo

P2D_RE = re.compile(
    r"^(?:Get(?:Position|Tangent)\w*\|[^=\s\t]+\t[nuv]:.+|GetLength\tn:.+)$", re.M)


def wlog(msg):
    line = time.strftime("[%H:%M:%S] ") + msg
    try:
        with open(WLOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    print(line, flush=True)


def set_status(stage, extra=""):
    try:
        with open(STATUS, "w", encoding="utf-8") as f:
            json.dump({"stage": stage, "extra": extra, "t": time.time()}, f)
    except Exception:
        pass


def bin_ls():
    """Lista archivos del bin via API v3 con sesion cookie."""
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.addheaders = [("User-Agent", "luau")]
    try:
        with op.open(f"https://filebin.net/{BIN}", timeout=20) as r:
            r.read()
    except Exception:
        pass
    try:
        with op.open(f"https://filebin.net/api/v3/file/browse?bin={BIN}",
                     timeout=20) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
        files = data.get("files", [])
        return [(f.get("filename", ""), f.get("bytes", 0)) for f in files]
    except Exception as e:
        return None


def bin_get(name):
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.addheaders = [("User-Agent", "luau")]
    try:
        with op.open(f"https://filebin.net/{BIN}", timeout=20) as r:
            r.read()
    except Exception:
        pass
    try:
        with op.open(f"https://filebin.net/{BIN}/{name}", timeout=25) as r:
            return r.read().decode("latin-1")
    except Exception as e:
        wlog(f"[bin] get {name}: {e}")
        return None


def valid_entries(text):
    return P2D_RE.findall(text)


# ---------------- fase A: esperar al user ----------------
def wait_for_probe():
    wlog("FASE A: esperando probe2 del user en filebin " + BIN)
    set_status("waiting_probe")
    seen = set()
    deadline = time.time() + MAX_WAIT_H * 3600
    while time.time() < deadline:
        ls = bin_ls()
        if ls is None:
            wlog("[bin] API inaccesible, reintentando")
        else:
            for name, sz in ls:
                if not re.match(r"path2d2_\d+\.txt", name):
                    continue
                if name in seen:
                    continue
                seen.add(name)
                body = bin_get(name)
                if body is None:
                    continue
                ents = valid_entries(body)
                wlog(f"[bin] {name} ({sz}B): {len(ents)} lineas validas")
                if len(ents) >= 12:
                    path = MITM + "/loader_path2d.txt"
                    with open(path, "w", encoding="latin-1") as f:
                        f.write(body)
                    wlog(f"[+] datos del loader guardados: {path}")
                    return path
        time.sleep(POLL)
    wlog("[!] TIMEOUT esperando al user")
    set_status("timeout_waiting")
    return None


# ---------------- fase B: aplicar + relanzar ----------------
def apply_and_launch(path):
    set_status("applying")
    wlog("FASE B: apply_p2d2.py " + path)
    r = subprocess.run([sys.executable, HERE + "/scripts/apply_p2d2.py", path],
                       capture_output=True, text=True, timeout=600)
    wlog(r.stdout[-2000:])
    if r.returncode != 0:
        wlog("[!] apply_p2d2 fallo:\n" + r.stderr[-1500:])
        set_status("apply_failed", r.stderr[-300:])
        return False
    wlog("FASE B2: launch_mitm.py (harness + driver vivos)")
    r2 = subprocess.run([sys.executable, HERE + "/scripts/launch_mitm.py"],
                        capture_output=True, text=True, timeout=120)
    wlog(r2.stdout[-500:])
    return r2.returncode == 0


# ---------------- fase C: monitor del replay ----------------
def tail_marks():
    """Lee el log y extrae marcas clave."""
    marks = {"l2dswap": False, "mitm": 0, "mitmdone": 0, "state294": 0,
             "loadstrings": [], "errors": []}
    try:
        with open(MITM + "/mitm_harness.log", encoding="latin-1") as f:
            log = f.read()
    except Exception:
        return marks
    if "\0L2DSWAP" in log or "L2DSWAP" in log:
        marks["l2dswap"] = True
    marks["mitm"] = len(re.findall(r"\x00?MITM \d+ ", log))
    marks["mitmdone"] = len(re.findall(r"\x00?MITMDONE \d+ ", log))
    marks["state294"] = log.count("State294")
    for m in re.finditer(r"loadstring\(\) of (\d+) bytes", log):
        n = int(m.group(1))
        if n not in marks["loadstrings"]:
            marks["loadstrings"].append(n)
    for m in re.finditer(r"(Luarmor V4 loader failed[^\n]{0,120}|buffer[^\n]{0,80}range[^\n]{0,40})", log):
        marks["errors"].append(m.group(0)[:150])
    return marks


def resp_files():
    try:
        return sorted(f for f in os.listdir(MITM) if re.match(r"resp_\d+\.luau$", f))
    except Exception:
        return []


def monitor():
    wlog("FASE C: monitor del replay en vivo")
    set_status("monitoring")
    t0 = time.time()
    base_resp = None
    payload_at = None
    last_done = 0
    while time.time() - t0 < MONITOR_MAX_S:
        time.sleep(20)
        mk = tail_marks()
        rf = resp_files()
        if base_resp is None and rf:
            # primera foto: chunks del loader (3) + handshake (1)
            base_resp = rf
            wlog(f"[monitor] baseline resp: {rf}")
        now = time.time()
        if mk["mitmdone"] != last_done:
            last_done = mk["mitmdone"]
            wlog(f"[monitor] t+{int(now-t0)}s MITM done={mk['mitmdone']} "
                 f"l2dswap={mk['l2dswap']} resp={rf}")
        # payload = resp NUEVO mas alla del baseline, o un 5o request
        if base_resp and len(rf) > len(base_resp):
            if payload_at is None:
                payload_at = now
                wlog(f"[!!!] PAYLOAD DETECTADO: resp nuevos {set(rf)-set(base_resp)}")
                set_status("payload_arriving", ",".join(rf))
            if now - payload_at > PAYLOAD_GRACE_S:
                wlog("[+] ventana de descarga cerrada, capturando")
                return True
        # errores fatales conocidos
        if mk["errors"]:
            wlog("[monitor] error: " + "; ".join(mk["errors"][-3:]))
            if mk["state294"]:
                set_status("state294", "; ".join(mk["errors"][-1:]))
                return False
        # termino bien? (script premium ejecutandose: loadstring grande nuevo)
        big_new = [n for n in mk["loadstrings"] if n > 50000]
        if payload_at and big_new:
            wlog(f"[monitor] loadstring premium: {big_new}")
            time.sleep(30)
            return True
    wlog("[!] monitor agoto el tiempo")
    set_status("monitor_timeout")
    return False


# ---------------- fase D: capturar ----------------
def capture():
    set_status("capturing")
    wlog("FASE D: capturando payload")
    os.makedirs(OUTDIR, exist_ok=True)
    import shutil
    ts = time.strftime("%H%M%S")
    n = 0
    for f in resp_files():
        shutil.copy2(os.path.join(MITM, f), os.path.join(OUTDIR, f"{ts}_{f}"))
        n += 1
    for logf in ("mitm_harness.log", "driver_console.log", "requests.log"):
        p = os.path.join(MITM, logf)
        if os.path.exists(p):
            shutil.copy2(p, os.path.join(OUTDIR, f"{ts}_{logf}"))
    wlog(f"[+] {n} resp copiados a {OUTDIR}")
    set_status("captured", f"{n} files @ {ts}")
    return True


def main():
    wlog("=== AUTOWATCH arrancado ===")
    path = wait_for_probe()
    if not path:
        return 1
    if not apply_and_launch(path):
        return 2
    ok = monitor()
    capture()
    wlog(f"=== AUTOWATCH terminado ok={ok} ===")
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
