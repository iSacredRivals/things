#!/usr/bin/env python3
"""Driver MITM v4: vigilanda el log del harness (los prints \\0MITM llevan un
padding de 8KB que fuerza el flush del stdout buffer), reenvia cada request EN
VIVO a los servers reales con method/body/headers fieles, y escribe
mitm/resp_N.luau (modulo con body + status + HEADERS reales).

Lineas del harness:
    \\0MITM <n> <label> <url>
    \\0MITMOPT <n> <method>
    \\0MITMHDR <n> <headers CRLF>
    \\0MITMBODY <n> <body \\x01=\\n>
"""
import os, sys, time, re, urllib.request, urllib.error, ssl, json

MITM_DIR = "/home/z/my-project/deobf/aurora/analysis/replay/mitm"
LOG = MITM_DIR + "/mitm_harness.log"
REQLOG = MITM_DIR + "/requests.log"
UA = "luau"

def lua_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'

def long_string(s: str) -> str:
    level = 0
    while ("]" + "=" * level + "]") in s:
        level += 1
    # cuerpos que terminan en "]" colisionan con el closer "]]" (auto-solape):
    # bump a nivel 1 para que el closer sea "]=]"
    if level == 0 and s.endswith("]"):
        level = 1
    eq = "=" * level
    return "[" + eq + "[\n" + s + "]" + eq + "]"

def log(s):
    with open(REQLOG, "a", encoding="utf-8") as f:
        f.write(time.strftime("[%H:%M:%S] ") + s + "\n")

def forward(url, method="GET", body="", headers=None):
    hdrs = {"User-Agent": UA}
    if headers:
        hdrs.update(headers)
    data = body.encode("latin-1", "replace") if body else None
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=90, context=ctx) as r:
            return r.status, r.read().decode("latin-1"), dict(r.headers.items())
    except urllib.error.HTTPError as e:
        try:
            return e.code, e.read().decode("latin-1"), dict(e.headers.items())
        except Exception:
            return e.code, "", dict(e.headers.items())
    except Exception as e:
        return 0, "ERROR: " + str(e), {}

class Pending:
    def __init__(self, n, label, url):
        self.n, self.label, self.url = n, label, url
        self.method, self.body, self.headers = "GET", "", {}

def main():
    print(f"[driver v4] vigilando {LOG}")
    log("driver v4 start")
    sent = set()
    pending = {}
    pos = 0
    while True:
        try:
            with open(LOG, "r", errors="replace") as f:
                f.seek(pos)
                chunk = f.read()
                pos = f.tell()
        except FileNotFoundError:
            time.sleep(0.3)
            continue

        for line in chunk.split("\n"):
            if not line.startswith("\x00"):
                continue
            parts = line.split(" ", 3)
            tag = parts[0][1:]
            if tag == "MITM" and len(parts) >= 4:
                n = int(parts[1])
                if n not in pending:
                    pending[n] = Pending(n, parts[2], parts[3].strip())
            elif tag == "MITMOPT" and len(parts) >= 3:
                n = int(parts[1])
                if n in pending:
                    pending[n].method = parts[2].strip() or "GET"
            elif tag == "MITMHDR" and len(parts) >= 3:
                n = int(parts[1])
                if n in pending:
                    for h in parts[2].split("\r\n"):
                        if ":" in h:
                            hk, _, hv = h.partition(":")
                            pending[n].headers[hk.strip()] = hv.strip()
            elif tag == "MITMBODY" and len(parts) >= 3:
                n = int(parts[1])
                if n in pending:
                    pending[n].body = parts[2].replace("\x01", "\n")

        for n in sorted(pending):
            if n in sent:
                continue
            p = pending[n]
            sent.add(n)
            print(f"[driver] MITM #{n} {p.label} {p.method} -> {p.url[:140]}")
            log(f"REQ #{n} {p.label} {p.method} {p.url} headers={json.dumps(p.headers)} body={p.body[:200]!r}")
            code, body, hdrs = forward(p.url, p.method, p.body, p.headers)
            print(f"[driver]   HTTP {code} len={len(body)} headers={json.dumps(hdrs)}")
            log(f"RESP #{n} HTTP {code} len={len(body)} headers={json.dumps(hdrs)} :: {body[:300]!r}")
            # modulo con body + status + headers REALES: caso original Y
            # variantes lowercase/Title (el VM busca "Sihir", "kkr", etc.)
            hdr_out = {}
            for k, v in hdrs.items():
                hdr_out[k] = v
                lk = k.lower()
                if lk != k:
                    hdr_out[lk] = v
                tk = lk.capitalize()
                if tk != k and tk != lk:
                    hdr_out[tk] = v
            hdr_lua = "{" + ", ".join(f"[{lua_str(k)}] = {lua_str(v)}" for k, v in hdr_out.items()) + "}"
            out = os.path.join(MITM_DIR, f"resp_{n}.luau")
            # ESCRITURA ATOMICA: escribir tmp + rename (el poll del harness puede
            # cachear un error de compilacion si lee el archivo a mitad de write)
            tmp = out + ".tmp"
            with open(tmp, "w", encoding="latin-1", newline="\n") as f:
                f.write(f"return {{ __body = {long_string(body)}, __code = {code}, __headers = {hdr_lua} }}\n")
            os.replace(tmp, out)
        pending.clear()
        time.sleep(0.3)

if __name__ == "__main__":
    main()
