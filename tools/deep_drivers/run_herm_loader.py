#!/usr/bin/env python3
"""Replay driver for the hermanos LOADER (obf_3.lua, 363 KB, Luraph v14.5 VM).

The loader is the orchestrator: Luarmor auth (syn.request) -> TranslatorModule
(dump_5) -> GitHub fetches (WindUI, icons) -> the hub payload.
Replays the captured bodies via http_responses and logs requested URLs +
returned values so the next mapping round can be built.
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

INPUT = "/home/z/my-project/downloads_cdn/obf_3.lua"
DUMPS = "/home/z/my-project/downloads_cdn/hermanoshub"

# default replay map: pastefy kill-switch + github files (as captured)
DEFAULT_MAP = [
    ("pastefy.app/LPwtBxk4", "/home/z/my-project/downloads_cdn/pastefy_LPwtBxk4.lua"),
    ("hermanos-dev/hermanos-hub", DUMPS + "/dump_5_http.lua"),  # placeholder: refined per URL
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--locale", default="es")
    ap.add_argument("--raw", default="/tmp/herm_loader_raw.txt")
    ap.add_argument("--out", default="/tmp/herm_loader_trace.luau")
    ap.add_argument("--map", action="append", default=[],
                    help="url-substr=path (repeatable)")
    ap.add_argument("--timeout", type=int, default=400)
    ap.add_argument("--budget", type=int, default=180)
    ap.add_argument("--vmcap", type=int, default=250_000_000)
    ap.add_argument("--plaincap", type=int, default=50_000_000)
    ap.add_argument("--extra", action="append", default=[])
    ap.add_argument("--prelude", default="",
                    help="extra prelude code appended after the locale setup")
    args = ap.parse_args()

    source = open(INPUT, encoding="latin-1").read()
    spin = max(args.budget, 60)
    guarded, n_loops, n_vm = guards.inject(source, args.vmcap, args.plaincap, spin)
    print(f"[*] guards: {n_loops} loops ({n_vm} VM dispatch)", file=sys.stderr)

    http_responses = []
    for m in args.map:
        pat, _, path = m.partition("=")
        if not os.path.exists(path):
            sys.exit(f"[!] missing file {path}")
        body = open(path, encoding="latin-1").read()
        http_responses += [pat, body]
        print(f"[*] http map: {pat!r} -> {path} ({len(body)} B)", file=sys.stderr)

    prelude = (
        "setprop(game:GetService('LocalizationService'), 'RobloxLocaleId', '%s')"
        "; rawset(genv, 'script_mode', 'PVP')"
        "; rawset(G, 'script_mode', 'PVP')"
    ) % args.locale
    if args.prelude:
        prelude += "; " + args.prelude

    cfg = {
        "heartbeat": 0,
        "time_budget": args.budget,
        "prelude": prelude,
        "chunk_min": 512,
        "dump_strings": True,
        "executor": "Delta",
        "log_return": "3",
        "vm_pause": True,
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
    print(f"[*] running loader replay ({len(http_responses)//2} http bodies)...", file=sys.stderr)
    body, err = harness.run_once(luau, guarded, cfg, FakeJob.trace_path, args.timeout, True)

    if body is None:
        print(f"[!] run failed: {str(err)[:2000]}", file=sys.stderr)
        with open(args.raw, "w", encoding="utf-8") as f:
            f.write(harness.LAST_RAW[0] or str(err))
        sys.exit(1)

    with open(args.raw, "w", encoding="utf-8") as f:
        f.write(harness.LAST_RAW[0])

    chunks = re.findall(r"\x00CHUNK (\S+)\n", body)
    print(f"[+] chunks: {chunks}", file=sys.stderr)
    print(f"[+] statements: {body.count(chr(10)) + 1}", file=sys.stderr)
    m = re.search(r"run status: (.*)", body)
    print(f"[+] status: {m.group(1) if m else '?'}", file=sys.stderr)
    m2 = re.findall(r"--   (https?://\S+)", body)
    print(f"[+] URLs requested: {sorted(set(m2))}", file=sys.stderr)


if __name__ == "__main__":
    main()
