#!/usr/bin/env python3
"""Validate the offline Path2D model against REAL device answers.

The loader (obf_5) probe was run on the user's device (Task 61): 13 answers
captured in aurora/loader_path2d.txt. This driver replays the EXACT same probe
(Frame 193x224, 6 CPs, same query order) through the engine's envlog runtime
with --cfg p2d_check=true, so envlog prints \0P2DCHECK lines comparing the
offline model's computed answer against the recorded real-device answer for
every query. Bit-exact -> 'same'; any deviation -> 'DIFF'.

Usage: python3 p2d_validate.py
"""
import os
import re
import sys

HERE = "deobf"
sys.path.insert(0, HERE)

import harness  # noqa: E402

REAL_FILE = "aurora_qo/loader_path2d.txt"
PROBE = "/home/z/my-project/scripts/p2d_probe_loader.lua"
HARNESS_OUT = "/home/z/my-project/scripts/p2d_check_harness.luau"


def main():
    # 1) load the REAL device answers as the recorded cache
    harness.P2D_CACHE.clear()
    real = {}
    with open(REAL_FILE, encoding="utf-8") as f:
        for line in f:
            k, _, v = line.rstrip("\n").partition("\t")
            if k:
                real[k] = v
                harness.P2D_CACHE[k] = v
    print("[*] %d real-device answers loaded from %s" % (len(real), REAL_FILE))

    # 2) run the probe through envlog with p2d_check
    source = open(PROBE, encoding="utf-8").read()
    cfg = {"p2d_check": True, "heartbeat": 2, "time_budget": 60}
    luau = harness.find_luau()
    body, err = harness.run_once(luau, source, cfg, HARNESS_OUT, 90, keep=True)
    if err:
        print("[!] harness error:", err[:2000])
        return 1

    # 3) the probe's own printed answers (what the model returned live)
    m = re.search(r"==P2D-LOADER-MODEL==\n(.*?)==P2D-LOADER-MODEL-END==", body, re.S)
    model_out = {}
    if m:
        for line in m.group(1).strip().splitlines():
            k, _, v = line.partition("\t")
            model_out[k] = v

    # 4) P2DCHECK lines (model vs recorded real answer) live in the raw stdout
    raw = harness.LAST_RAW[0]
    checks = re.findall(r"P2DCHECK ([^\n]+)", raw)

    print("\n=== MODEL vs REAL DEVICE (loader probe, Frame 193x224, 6 CPs) ===")
    nsame = ndiff = 0
    seen = set()
    for line in checks:
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        key, rec, model, verdict = parts[0], parts[1], parts[2], parts[3]
        seen.add(key)
        if verdict == "same":
            nsame += 1
            print("  OK    %s" % key)
        else:
            ndiff += 1
            print("  DIFF  %s\n          real  : %s\n          model : %s" % (key, rec, model))
    print("\n%s: %d same, %d DIFF" % ("VERDICT" if checks else "NO P2DCHECK LINES", nsame, ndiff))

    # 5) also compare the model-computed output block with the real file
    print("\n=== model output vs real file (independent of P2DCHECK) ===")
    miss = []
    for k, v in real.items():
        mv = model_out.get(k)
        if mv is None:
            miss.append(k)
        elif mv != v:
            print("  DIFF  %s\n          real  : %s\n          model : %s" % (k, v, mv))
        else:
            print("  OK    %s" % k)
    if miss:
        print("  MISSING from model output:", miss)
    return 0 if (ndiff == 0 and not miss) else 2


if __name__ == "__main__":
    sys.exit(main())
