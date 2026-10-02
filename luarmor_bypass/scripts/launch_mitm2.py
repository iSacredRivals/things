#!/usr/bin/env python3
"""Lanza el harness MITM + driver de forma PERSISTENTE (start_new_session=True
- sobrevive al cleanup del tool session). Antes de lanzar: regenera el harness
con stub fresco (tokens de sesion nuevos) y limpia resp_*.luau viejos."""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(os.path.dirname(HERE))
MITM_DIR = os.path.join(HERE, "..", "mitm")
LUAU = os.path.join(PKG, "deobf", "bin", "luau")
DRIVER = os.path.join(HERE, "mitm_driver2.py")
MAKER = os.path.join(HERE, "make_mitm2.py")


def main():
    regen = "--no-regen" not in sys.argv
    if regen:
        print("[*] regenerando harness con stub fresco...")
        r = subprocess.run([sys.executable, MAKER], capture_output=True, text=True, timeout=180)
        tail = (r.stdout or "").strip().split("\n")[-4:]
        print("\n".join("    " + l for l in tail))
        if r.returncode != 0:
            print("[-] make fallo:", (r.stderr or "")[-500:])
            sys.exit(1)
    else:
        print("[*] sin regeneracion (usa harness actual)")

    # limpiar estado de sesiones anteriores
    for f in os.listdir(MITM_DIR):
        if f.startswith("resp_"):
            os.remove(os.path.join(MITM_DIR, f))
    for f in ("mitm_harness.log", "requests.log", "driver_console.log", "pids.txt"):
        p = os.path.join(MITM_DIR, f)
        if os.path.exists(p):
            os.remove(p)

    log = open(os.path.join(MITM_DIR, "mitm_harness.log"), "w")
    drv = open(os.path.join(MITM_DIR, "driver_console.log"), "w")
    h = subprocess.Popen([LUAU, "mitm_harness.luau"], cwd=MITM_DIR,
                         stdout=log, stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL, start_new_session=True)
    time.sleep(2)
    d = subprocess.Popen([sys.executable, DRIVER], cwd=MITM_DIR,
                         stdout=drv, stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL, start_new_session=True)
    print(f"harness PID {h.pid}, driver PID {d.pid}")
    with open(os.path.join(MITM_DIR, "pids.txt"), "w") as f:
        f.write(f"{h.pid} {d.pid}\n")


if __name__ == "__main__":
    main()
