#!/usr/bin/env python3
"""hermanos loader FAST replay v2: NO ptrace.

Task 67's fast run kept ptrace=True: every table.create went through the
Delta-closure wrapper whose 10-frame debug.info stack-walk got TRACED
(~26 ms per call) -> the decode "took 13 minutes" and ended in
create(garbage) (Luraph timing anti-tamper). With ptrace off the wrapper
runs at Lua speed; the P2D stage-key answers were verified bit-exact
against the device (==P2D==, unparented ScreenGui — the loader never
parents its probe ScreenGui, confirmed in the guarded trace).
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
    ap.add_argument("--raw", default="samples/output/herm_fast2_raw.txt")
    ap.add_argument("--out", default="samples/output/herm_fast2_trace.luau")
    ap.add_argument("--map", action="append", default=[])
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--budget", type=int, default=3000)
    ap.add_argument("--prelude", default="")
    ap.add_argument("--arg", default="", help="chunk varargs (chunk_args cfg)")
    args = ap.parse_args()

    source = open(INPUT, encoding="latin-1").read()

    http_responses = []
    if not args.map:
        http_responses = [
            "pastefy.app/LPwtBxk4", open("/home/z/my-project/downloads_cdn/pastefy_LPwtBxk4.lua", encoding="latin-1").read(),
            "hermanos-dev/hermanos-hub", open(DUMPS + "/dump_5_http.lua", encoding="latin-1").read(),
        ]
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
        "heartbeat": 0,
        "prelude": prelude,
        "chunk_min": 512,
        "dump_strings": True,
        "executor": "Delta",
        "log_return": "3",
        "http_responses": http_responses or None,
    }
    if args.arg:
        cfg["chunk_args"] = args.arg

    class FakeArgs:
        timeout = args.timeout
        keep_harness = True
        studio = False
        studio_wait = 0

    class FakeJob:
        args = FakeArgs()

    FakeJob.trace_path = args.out + ".harness.luau"

    luau = harness.find_luau()
    print(f"[*] FAST v2 run (no ptrace, budget {args.budget}s, timeout {args.timeout}s)...", file=sys.stderr)
    body, err = harness.run_once(luau, source, cfg, FakeJob.trace_path, args.timeout, True)

    raw = harness.LAST_RAW[0]
    with open(args.raw, "w", encoding="utf-8") as f:
        f.write(raw)
    if body is None:
        print(f"[!] run failed: {str(err)[:2500]}", file=sys.stderr)
        return 1

    chunks = re.findall(r"\x00CHUNK (\S+)\n", body)
    print(f"[+] chunks: {chunks}", file=sys.stderr)
    print(f"[+] statements: {body.count(chr(10)) + 1}", file=sys.stderr)
    m = re.search(r"run status: (.*)", body)
    print(f"[+] status: {m.group(1) if m else '?'}", file=sys.stderr)
    m2 = re.findall(r"--   (https?://\S+)", body)
    print(f"[+] URLs: {sorted(set(m2))}", file=sys.stderr)
    for line in raw.splitlines():
        if "\x00P2D " in line:
            print("[P2D] " + line.split("\0P2D ", 1)[1].replace("\0", ""), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
