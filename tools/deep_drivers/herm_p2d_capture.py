#!/usr/bin/env python3
"""Short-budget capture of the hermanos loader (obf_3.lua) P2D probe:
same prelude as run_herm_fast.py but a short time budget so the run stops
right after the probe; the raw output keeps the [newindex] ptrace lines
(ScreenGui/Frame/Path2D .Parent assignments) and the \0P2D model answers.
"""
import argparse
import os
import re
import sys

ENGINE = "deobf"
sys.path.insert(0, ENGINE)
os.chdir(ENGINE)

import harness  # noqa: E402

INPUT = "/home/z/my-project/downloads_cdn/obf_3.lua"
DUMPS = "/home/z/my-project/downloads_cdn/hermanoshub"

TABLE_PROXY = (
    "local __realT = env.table; "
    "local __smt = env.setmetatable; "
    "local __dbg, __rp = env.debug, env.pcall; "
    "local __proxy = __smt({}, { __index = __realT }); "
    "__proxy.create = function(n, ...) "
    "for l = 3, 12 do local ok, s = __rp(__dbg.info, l, 'sl') "
    "if not ok or s == nil then break end end "
    "return __realT.create(n, ...) end; "
    "env.table = __proxy"
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--locale", default="es")
    ap.add_argument("--raw", default="samples/output/herm_p2dcap_raw.txt")
    ap.add_argument("--out", default="samples/output/herm_p2dcap_trace.luau")
    ap.add_argument("--timeout", type=int, default=200)
    ap.add_argument("--budget", type=int, default=75)
    args = ap.parse_args()

    source = open(INPUT, encoding="latin-1").read()

    http_responses = [
        "pastefy.app/LPwtBxk4", open("/home/z/my-project/downloads_cdn/pastefy_LPwtBxk4.lua", encoding="latin-1").read(),
        "hermanos-dev/hermanos-hub", open(DUMPS + "/dump_5_http.lua", encoding="latin-1").read(),
    ]

    prelude = (
        "setprop(game:GetService('LocalizationService'), 'RobloxLocaleId', '%s'); "
        "rawset(genv, 'script_mode', 'PVP'); rawset(G, 'script_mode', 'PVP'); "
        "genv.script_key = 'PLACEHOLDER_KEY'; rawset(G, 'script_key', 'PLACEHOLDER_KEY'); "
        "rawset(env, 'script_key', 'PLACEHOLDER_KEY'); "
        "genv.key = 'PLACEHOLDER_KEY'; rawset(env, 'key', 'PLACEHOLDER_KEY'); "
        "rawset(env, 'gethwid', function() return "
        "'d3b14c1f2a9b7e8c4d5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c' end); "
        "rawset(env, 'getexecutorname', function() return 'Delta' end); "
        "%s"
    ) % (args.locale, TABLE_PROXY)

    cfg = {
        "time_budget": args.budget,
        "max_stmts": 50_000_000,
        "heartbeat": 30,
        "ptrace": True,
        "prelude": prelude,
        "chunk_min": 512,
        "dump_strings": True,
        "executor": "Delta",
        "log_return": "3",
        "http_responses": http_responses,
    }

    class FakeArgs:
        timeout = args.timeout
        keep_harness = True
        studio = False
        studio_wait = 0

    class FakeJob:
        args = FakeArgs()

    FakeJob.trace_path = args.out + ".harness.luau"

    luau = harness.find_luau()
    print(f"[*] CAPTURE run (budget {args.budget}s)...", file=sys.stderr)
    body, err = harness.run_once(luau, source, cfg, FakeJob.trace_path, args.timeout, True)

    raw = harness.LAST_RAW[0]
    with open(args.raw, "w", encoding="utf-8") as f:
        f.write(raw)
    if body is None:
        print(f"[!] run failed: {str(err)[:1500]}", file=sys.stderr)
    m = re.search(r"run status: (.*)", body or "")
    print(f"[+] status: {m.group(1) if m else '?'}", file=sys.stderr)
    for line in raw.splitlines():
        if "\0P2D " in line:
            print("[P2D] " + line.split("\0P2D ", 1)[1], file=sys.stderr)


if __name__ == "__main__":
    main()
