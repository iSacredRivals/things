#!/usr/bin/env python3
"""FAST hermanos loader replay: obf_3.lua RAW (no guards) through the envlog
environment — full-speed VM decode like the QO mitm harness.

Config: Delta executor, table.create Lua-closure wrapper (Delta wraps its
stdlib), pastefy + http_responses replay, budget 5400.
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

# Delta stdlib wrapper: table.create as a Lua closure (Delta wraps the stdlib)
# + the stack-walk inside (the VM probes the call context; without the walk
# it answers "table overflow" tamper)
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
    ap.add_argument("--raw", default="/tmp/herm_fast_raw.txt")
    ap.add_argument("--out", default="/tmp/herm_fast_trace.luau")
    ap.add_argument("--map", action="append", default=[])
    ap.add_argument("--timeout", type=int, default=800)
    ap.add_argument("--budget", type=int, default=2400)
    ap.add_argument("--prelude", default="")
    args = ap.parse_args()

    source = open(INPUT, encoding="latin-1").read()

    http_responses = []
    for m in args.map:
        pat, _, path = m.partition("=")
        if not os.path.exists(path):
            sys.exit(f"[!] missing file {path}")
        body = open(path, encoding="latin-1").read()
        http_responses += [pat, body]
        print(f"[*] http map: {pat!r} -> {path} ({len(body)} B)", file=sys.stderr)

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
    if args.prelude:
        prelude += "; " + args.prelude

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
        "http_responses": http_responses or None,
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
    print(f"[*] FAST run (no guards, budget {args.budget}s)...", file=sys.stderr)
    body, err = harness.run_once(luau, source, cfg, FakeJob.trace_path, args.timeout, True)

    if body is None:
        print(f"[!] run failed: {str(err)[:2500]}", file=sys.stderr)
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
    print(f"[+] URLs: {sorted(set(m2))}", file=sys.stderr)


if __name__ == "__main__":
    main()
