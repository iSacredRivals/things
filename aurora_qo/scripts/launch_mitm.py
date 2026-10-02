#!/usr/bin/env python3
"""Lanza el harness MITM + driver de forma PERSISTENTE (start_new_session=True
- sobrevive al cleanup del tool session, verificado con los replays previos)."""
import subprocess, sys, os, time

MITM_DIR = "/home/z/my-project/deobf/aurora/analysis/replay/mitm"
LUAU = "/home/z/my-project/deobf/deobf/bin/luau"
DRIVER = "/home/z/my-project/deobf/aurora/scripts/mitm_driver.py"

def main():
    clean = "--keep" not in sys.argv
    if clean:
        for f in os.listdir(MITM_DIR):
            if f.startswith("resp_"):
                os.remove(os.path.join(MITM_DIR, f))
        for f in ("mitm_harness.log", "requests.log", "driver_console.log"):
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
