#!/usr/bin/env python3
"""Extrae los chunks (\0CHUNK key + hex) del log del harness MITM.

Al final de la corrida, envlog dumpea cada fuente grande que paso por
loadstring como:
    \0CHUNK <key>\n<hex>\n
El orden: bootstrapper (764KB, conocido), loader (el nuevo de este script),
payload (el script protegido final, Luraph v15).

Uso: extract_chunks2.py <log> [outdir]
"""
import re
import sys

REAL_BOOT_MD5 = "1b6abc28ad70b657836ac227af71e5cc"
KNOWN_SIZE = 764123


def main():
    log_path = sys.argv[1] if len(sys.argv) > 1 else \
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mitm", "mitm_harness.log")
    outdir = sys.argv[2] if len(sys.argv) > 2 else \
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mitm")
    src = open(log_path, "rb").read().decode("latin-1")
    print(f"[*] log: {len(src)} B")

    found = re.findall(r"\x00CHUNK (\S+)\n([0-9a-f]*)\n", src)
    if not found:
        print("[!] sin chunks aun (la corrida no termino o nada paso por loadstring)")
        return 1
    for i, (key, hx) in enumerate(found):
        data = bytes.fromhex(hx) if hx else b""
        path = f"{outdir}/chunk{i}_{key[:20]}.lua"
        with open(path, "wb") as f:
            f.write(data)
        kind = "?"
        if len(data) == 0:
            kind = "VACIO (no dumpeado)"
        elif b"Luarmor V4 bootstrapper" in data[:400]:
            kind = "bootstrapper (conocido)"
        else:
            kind = f"LOADER/PAYLOAD ({len(data)} B)"
        print(f"[+] chunk{i} key={key} -> {path} ({len(data)} B) [{kind}]")
        print(f"    head: {data[:100]!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
