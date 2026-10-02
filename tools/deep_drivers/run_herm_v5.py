#!/usr/bin/env python3
"""hermanos loader replay v5: accelerated clock + session key + HB telemetry.

Decision tree this run resolves:
- gate CLOSED (VM spins until the 902s deadline then create(garbage)):
  with the clock accelerated FOLD the deadline hits at ~902/FOLD real seconds
  -> run completes fast, status "script error ... create ... size out of range"
  -> script_key (32-char real format) did NOT open the gate.
- gate OPEN (payload decode runs): count-based decode unaffected by the clock
  -> statements/HBs keep flowing, CHUNK appears, run takes ~81+decode s.

Telemetry: heartbeat=2 gives clean phase markers in stdout (survives kills).
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

SESSION_KEY = "LbdcJNWbjhlelJHknRFNRcbBzibDAyTl"

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


def accel_clock(fold):
    if fold <= 0:
        return ""
    return (
        "local __os = env.os; local __pc = env.pcall; "
        "local __oc = __os and __os.clock; "
        "local __t0 = (__oc and __oc()) or 0; "
        "local __ot = __os and __os.time; "
        "local __ep = (__ot and __ot()) or 0; "
        "local __f = %d; "
        "local function __now() return __t0 + (((__oc and __oc()) or __t0) - __t0) * __f end; "
        "if __os then "
        "__pc(rawset, __os, 'clock', __now); "
        "__pc(rawset, __os, 'time', function() return __ep + (__now() - __t0) end) "
        "end; "
        "rawset(env, 'tick', function() return __now() + 1.7e9 end); "
        "rawset(env, 'time', __now); "
        "rawset(env, 'elapsedTime', __now)"
    ) % fold


KEYSETUP = (
    "rawset(genv, 'script_key', '%s'); rawset(G, 'script_key', '%s'); "
    "rawset(env, 'script_key', '%s'); "
    "rawset(genv, 'key', '%s'); rawset(G, 'key', '%s'); rawset(env, 'key', '%s'); "
    "rawset(genv, 'key_expire', 0); rawset(genv, 'key_note', ''); "
    "rawset(genv, 'key_executions', 0)"
) % ((SESSION_KEY,) * 6)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--locale", default="es")
    ap.add_argument("--raw", default="samples/output/herm_v5_raw.txt")
    ap.add_argument("--out", default="samples/output/herm_v5_trace.luau")
    ap.add_argument("--timeout", type=int, default=1250)
    ap.add_argument("--budget", type=int, default=3000)
    ap.add_argument("--fold", type=int, default=2)
    ap.add_argument("--key", default=SESSION_KEY)
    args = ap.parse_args()

    keysetup = KEYSETUP.replace(SESSION_KEY, args.key)
    clock = accel_clock(args.fold)

    source = open(INPUT, encoding="latin-1").read()

    http_responses = [
        "pastefy.app/LPwtBxk4", open("/home/z/my-project/downloads_cdn/pastefy_LPwtBxk4.lua", encoding="latin-1").read(),
        "hermanos-dev/hermanos-hub", open(DUMPS + "/dump_5_http.lua", encoding="latin-1").read(),
    ]

    parts = [
        "setprop(game:GetService('LocalizationService'), 'RobloxLocaleId', '%s')" % args.locale,
        "rawset(genv, 'script_mode', 'PVP'); rawset(G, 'script_mode', 'PVP')",
        keysetup,
        clock,
        "rawset(env, 'gethwid', function() return "
        "'d3b14c1f2a9b7e8c4d5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c' end)",
        "rawset(env, 'getexecutorname', function() return 'Delta' end)",
        TABLE_PROXY,
    ]
    prelude = "; ".join(p for p in parts if p)

    cfg = {
        "time_budget": args.budget,
        "max_stmts": 50_000_000,
        "heartbeat": 2,
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
    print(f"[*] v5 run (fold={args.fold}, key={args.key[:6]}..., timeout {args.timeout}s)...", file=sys.stderr)
    body, err = harness.run_once(luau, source, cfg, FakeJob.trace_path, args.timeout, True)

    raw = harness.LAST_RAW[0]
    with open(args.raw, "w", encoding="utf-8") as f:
        f.write(raw)
    if body is None:
        print(f"[!] run failed: {str(err)[:2500]}", file=sys.stderr)
        return 1

    chunks = re.findall(r"\x00CHUNK (\S+)\n", body)
    print(f"[+] chunks: {chunks}", file=sys.stderr)
    m = re.search(r"run status: (.*)", body)
    print(f"[+] status: {m.group(1) if m else '?'}", file=sys.stderr)
    m2 = re.findall(r"--   (https?://\S+)", body)
    print(f"[+] URLs: {sorted(set(m2))}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
