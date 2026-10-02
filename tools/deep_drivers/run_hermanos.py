#!/usr/bin/env python3
"""Custom driver for the hermanos hub dump (Luraph v14.5.2, dump_5).

Runs the engine's v14 pipeline with full control over:
  - prelude (locale gate: LocalizationService.RobloxLocaleId -> real string)
  - http_responses (replay the bodies the user dumped, so the hub's stages run)
  - chunk_min (report every loadstring'd chunk)

Usage:
  python3 run_hermanos.py [--locale es] [--raw OUT] [--out OUT]
                          [--map "url-substr=path" ...] [--rounds N]
"""
import argparse
import os
import re
import sys

ENGINE = "deobf"
sys.path.insert(0, ENGINE)
os.chdir(ENGINE)

import harness  # noqa: E402
from obfuscators.luraph_v14 import guards  # noqa: E402

INPUT = "samples/hermanos_v145.lua"
DUMPS = "/home/z/my-project/hermanoshub"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--locale", default="es")
    ap.add_argument("--raw", default="samples/output/hermanos_raw.txt")
    ap.add_argument("--out", default="samples/output/hermanos_trace.lua")
    ap.add_argument("--map", action="append", default=[],
                    help="url-substring=path/to/dump (repeatable)")
    ap.add_argument("--http", action="append", default=[],
                    help="raw http_responses pair url-substring=path")
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--budget", type=int, default=240)
    ap.add_argument("--vmcap", type=int, default=250_000_000)
    ap.add_argument("--plaincap", type=int, default=5_000_000)
    ap.add_argument("--extra", action="append", default=[],
                    help="extra cfg KEY=VALUE (repeatable)")
    args = ap.parse_args()

    VMCAP = args.vmcap
    PLAINCAP = args.plaincap
    source = open(INPUT, encoding="latin-1").read()
    guarded, n_loops, n_vm = guards.inject(source, VMCAP, PLAINCAP)
    print(f"[*] guards: {n_loops} loops ({n_vm} VM dispatch)", file=sys.stderr)

    # http_responses map: flat [pattern, body, ...]
    http_responses = []
    for m in args.map:
        pat, _, path = m.partition("=")
        if not os.path.exists(path):
            sys.exit(f"[!] missing dump file {path}")
        body = open(path, encoding="latin-1").read()
        http_responses += [pat, body]
        print(f"[*] http map: {pat!r} -> {path} ({len(body)} B)", file=sys.stderr)

    prelude = (f"setprop(game:GetService('LocalizationService'), 'RobloxLocaleId', '{args.locale}')")
    cfg = {
        "heartbeat": 0,
        "time_budget": args.budget,
        "prelude": prelude,
        "chunk_min": 512,
        "dump_strings": True,
        "executor": "Wave",
    }
    if http_responses:
        cfg["http_responses"] = http_responses
    for kv in args.extra:
        k, _, v = kv.partition("=")
        cfg[k] = harness.parse_cfg_value(v) if hasattr(harness, "parse_cfg_value") else v

    class FakeArgs:
        timeout = args.timeout
        keep_harness = True
        studio = False
        studio_wait = 0

    class FakeJob:
        args = FakeArgs()

    FakeJob.trace_path = args.out + ".harness.luau"

    luau = harness.find_luau()
    print(f"[*] luau: {luau}", file=sys.stderr)
    print(f"[*] running (locale={args.locale}, {len(http_responses)//2} http bodies)...", file=sys.stderr)
    body, err = harness.run_once(luau, guarded, cfg, FakeJob.trace_path, args.timeout, True)
    harness.LAST_RAW[0] = (body or (err or ""))[:0] or harness.LAST_RAW[0]

    if body is None:
        print(f"[!] run failed: {err[:2000]}", file=sys.stderr)
        with open(args.raw, "w", encoding="utf-8") as f:
            f.write(harness.LAST_RAW[0] or str(err))
        sys.exit(1)

    with open(args.raw, "w", encoding="utf-8") as f:
        f.write(harness.LAST_RAW[0])

    # report what happened
    chunks = re.findall(r"\x00CHUNK (\S+)\n", body)
    urls = re.findall(r"(?:HttpGet|request|http_request|GetAsync|RequestAsync)\(([^)]*)\)", body)
    print(f"[+] raw saved: {args.raw}", file=sys.stderr)
    print(f"[+] chunks reported: {chunks}", file=sys.stderr)
    print("[+] statements:", body.count("\n") + 1, file=sys.stderr)


if __name__ == "__main__":
    main()
