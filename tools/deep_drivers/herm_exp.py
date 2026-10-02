#!/usr/bin/env python3
"""Hermanos experiment driver: custom prelude + probe, flat env."""
import argparse
import os
import sys

ENGINE = "deobf"
sys.path.insert(0, ENGINE)
os.chdir(ENGINE)

import harness  # noqa: E402
from obfuscators.luraph_v14 import guards  # noqa: E402

INPUT = "samples/hermanos_v145.lua"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prelude", default="")
    ap.add_argument("--locale", default="es")
    ap.add_argument("--hide", default="")
    ap.add_argument("--extra", action="append", default=[])
    ap.add_argument("--vmcap", type=int, default=5_000_000)
    ap.add_argument("--plaincap", type=int, default=5_000_000)
    ap.add_argument("--budget", type=int, default=40)
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--raw", default="/tmp/herm_exp.txt")
    args = ap.parse_args()

    source = open(INPUT, encoding="latin-1").read()
    guarded, n_loops, n_vm = guards.inject(source, args.vmcap, args.plaincap)
    print(f"[*] guards: {n_loops} loops ({n_vm} VM dispatch)", file=sys.stderr)

    prelude = ("setprop(game:GetService('LocalizationService'), 'RobloxLocaleId', '%s')"
               % args.locale)
    if args.prelude:
        prelude += "; " + args.prelude

    cfg = {"heartbeat": 0, "time_budget": args.budget, "prelude": prelude,
           "chunk_min": 512, "dump_strings": True, "executor": "Wave",
           "flat_env": True, "probe": True}
    if args.hide:
        cfg["env_hide"] = args.hide
    for kv in args.extra:
        k, _, v = kv.partition("=")
        cfg[k] = v

    class FakeArgs:
        timeout = args.timeout
        keep_harness = True
        studio = False
        studio_wait = 0

    class FakeJob:
        args = FakeArgs()

    FakeJob.trace_path = args.raw + ".harness.luau"
    luau = harness.find_luau()
    body, err = harness.run_once(luau, guarded, cfg, FakeJob.trace_path, args.timeout, True)
    if body is None:
        print("FAILED:", (err or "")[:1500])
        sys.exit(1)
    with open(args.raw, "w", encoding="utf-8") as f:
        f.write(harness.LAST_RAW[0])
    print(f"[+] raw: {args.raw}")
    # summary: last type() call before assert + assert position
    import re
    types = re.findall(r"\[call\]\ttype\(\"([^\"]+)\"\)", body)
    print(f"[*] walk processed {len(types)} keys; last: {types[-1] if types else '-'}")
    print("[*] assert:", "YES" if "assert(false)" in body else "NO")
    print("[*] status:", re.findall(r"run status: (.*)", body)[:1])
    chunks = re.findall(r"\x00CHUNK (\S+)\n", body)
    print("[*] chunks:", chunks)


if __name__ == "__main__":
    main()
