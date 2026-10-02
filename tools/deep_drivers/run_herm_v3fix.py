#!/usr/bin/env python3
"""hermanos loader FAST replay v3: frozen clock + real-format script_key.

Findings feeding this driver:
- The QO chain trace shows the bootstrapper sets getgenv().script_key =
  "LbdcJNWbjhlelJHknRFNRcbBzibDAyTl" (+ key/key_expire/key_note/key_executions)
  right before loadstring(loader)() -- the loader reads script_key as key
  material; our PLACEHOLDER_KEY gives garbage.
- v2 run ended at 983s = 81 + 902 (task.delay(902) watchdog): the VM spun
  773s and exited at the wall-clock deadline with create(garbage). Engine
  pre-phase is ~40x slower than a device -> any elapsed-time anti-debug
  check fires. FREEZING tick/time/elapsedTime/os.clock makes every delta 0.
  If the 773s loop is a time-deadline spin, the run will never end (timeout);
  if it is a genuine count-based decode, it completes with the frozen clock.
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

# frozen clock: every time read the script makes returns the same instant.
# offsets: tick looks like a Roblox tick (t0 + 1.7e9), os.time a fixed epoch.
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
) % (SESSION_KEY, SESSION_KEY, SESSION_KEY, SESSION_KEY, SESSION_KEY, SESSION_KEY)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--locale", default="es")
    ap.add_argument("--raw", default="samples/output/herm_fast3_raw.txt")
    ap.add_argument("--out", default="samples/output/herm_fast3_trace.luau")
    ap.add_argument("--timeout", type=int, default=1250)
    ap.add_argument("--budget", type=int, default=3600)
    ap.add_argument("--clock", default="real", choices=["freeze", "real", "offset"],
                    help="freeze=frozen instant, real=leave alone, offset=+1e6s")
    ap.add_argument("--key", default=SESSION_KEY)
    args = ap.parse_args()

    keysetup = KEYSETUP.replace(SESSION_KEY, args.key)
    clock = {"freeze": FROZEN_CLOCK, "real": "", "offset": FROZEN_CLOCK.replace(
        "__t0 + 1.7e9", "__t0 + 1.7e9 + 1000000")}[args.clock]

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
        "heartbeat": 0,
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
    print(f"[*] v3 run (clock={args.clock}, key={args.key[:6]}..., timeout {args.timeout}s)...", file=sys.stderr)
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
