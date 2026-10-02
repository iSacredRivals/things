#!/usr/bin/env python3
"""hermanos loader GUARDED replay v4: guards + table proxy + frozen clock +
real-format session key, long spin so the silent decode phase is not killed.

Task 67's guarded run WITH the table proxy showed REAL decode work (valid
table.create sizes 416/4523/31/4, 16764 statements) but was never concluded.
This driver reruns that configuration to completion:
- guards v14 (line-preserving, loop caps + spin watchdog)
- TABLE_PROXY: table.create as a Lua closure + stack walk (Delta wraps its
  stdlib; a pure C closure triggers the tamper response)
- frozen clock (tick/time/elapsedTime/os.clock at a fixed instant: every
  elapsed-time anti-debug delta reads 0)
- script_key = real 32-char Luarmor session key format (the bootstrapper
  sets getgenv().script_key right before launching the loader)
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

FROZEN_CLOCK = (
    "local __os = env.os; local __pc = env.pcall; "
    "local __oc = __os and __os.clock; "
    "local __t0 = (__oc and __oc()) or 0; "
    "local __ot = __os and __os.time; "
    "local __ep = (__ot and __ot()) or 0; "
    "local function __frz() return __t0 end; "
    "if __os then "
    "__pc(rawset, __os, 'clock', __frz); "
    "__pc(rawset, __os, 'time', function() return __ep end) "
    "end; "
    "rawset(env, 'tick', function() return __t0 + 1.7e9 end); "
    "rawset(env, 'time', __frz); "
    "rawset(env, 'elapsedTime', __frz)"
)

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
    ap.add_argument("--raw", default="samples/output/herm_v4_raw.txt")
    ap.add_argument("--out", default="samples/output/herm_v4_trace.luau")
    ap.add_argument("--timeout", type=int, default=2400)
    ap.add_argument("--budget", type=int, default=3600)
    ap.add_argument("--vmcap", type=int, default=400_000_000)
    ap.add_argument("--plaincap", type=int, default=60_000_000)
    ap.add_argument("--spin", type=int, default=1200,
                    help="v14 spin seconds (silent-loop watchdog)")
    args = ap.parse_args()

    source = open(INPUT, encoding="latin-1").read()
    guarded, n_loops, n_vm = guards.inject(source, args.vmcap, args.plaincap, args.spin)
    print(f"[*] guards: {n_loops} loops ({n_vm} VM dispatch)", file=sys.stderr)

    http_responses = [
        "pastefy.app/LPwtBxk4", open("/home/z/my-project/downloads_cdn/pastefy_LPwtBxk4.lua", encoding="latin-1").read(),
        "hermanos-dev/hermanos-hub", open(DUMPS + "/dump_5_http.lua", encoding="latin-1").read(),
    ]

    prelude = (
        "setprop(game:GetService('LocalizationService'), 'RobloxLocaleId', '%s'); "
        "rawset(genv, 'script_mode', 'PVP'); rawset(G, 'script_mode', 'PVP'); "
        "%s; %s; "
        "rawset(env, 'gethwid', function() return "
        "'d3b14c1f2a9b7e8c4d5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c' end); "
        "rawset(env, 'getexecutorname', function() return 'Delta' end); "
        "%s"
    ) % (args.locale, KEYSETUP, FROZEN_CLOCK, TABLE_PROXY)

    cfg = {
        "heartbeat": 0,
        "time_budget": args.budget,
        "prelude": prelude,
        "chunk_min": 512,
        "dump_strings": True,
        "executor": "Delta",
        "log_return": "3",
        "vm_pause": True,
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
    print(f"[*] v4 guarded run (timeout {args.timeout}s, spin {args.spin}s)...", file=sys.stderr)
    body, err = harness.run_once(luau, guarded, cfg, FakeJob.trace_path, args.timeout, True)

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
    return 0


if __name__ == "__main__":
    sys.exit(main())
