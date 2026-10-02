#!/usr/bin/env python3
"""Deep driver for dump_5 (Hermenos Hub stage-1, Luraph v14.5.2).

Runs the engine's FULL v14 pipeline (tidy trace -> .luau) with:
  - locale prelude (RobloxLocaleId = es/mx/pt/...) so the language gate opens
  - low --v14-vm-cap so a wrong-stage-key spin aborts in ~1s instead of 48s
    (the trace gathered before the spin is kept)
  - optional http_responses replay of the user's dumps

Usage:
  python3 run_dump5_deep.py [--locale es] [--vmcap 5000000] [--out OUT]
"""
import argparse
import os
import sys

ENGINE = "deobf"
sys.path.insert(0, ENGINE)
os.chdir(ENGINE)

import harness  # noqa: E402

INPUT = "/home/z/my-project/downloads_cdn/hermanoshub/dump_5_http.lua"
DUMPS = "/home/z/my-project/downloads_cdn/hermanoshub"
OUT = "/home/z/my-project/downloads_cdn/output/dump_5_deep.luau"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--locale", default="es")
    ap.add_argument("--vmcap", type=int, default=5_000_000)
    ap.add_argument("--plaincap", type=int, default=2_000_000)
    ap.add_argument("--budget", type=int, default=120)
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--raw", default="",
                    help="also save complete raw runtime output here")
    ap.add_argument("--map", action="append", default=[],
                    help="http_responses pair url-substr=path (repeatable)")
    ap.add_argument("--heartbeat", default="0")
    ap.add_argument("--prelude", default="",
                    help="extra prelude code appended after the locale setprop")
    ap.add_argument("--genv293", action="store_true",
                    help="populate getgenv() with the real Delta 293-key set")
    ap.add_argument("--no-flat-env", action="store_true",
                    help="do not set flat_env=true (prev session needed it)")
    ap.add_argument("--hide", default="",
                    help="env_hide list (comma-separated globals to drop from pairs)")
    ap.add_argument("--cfg", action="append", default=[],
                    help="extra envlog CFG KEY=VALUE (repeatable)")
    args_cli = ap.parse_args()

    http_responses = []
    for m in args_cli.map:
        pat, _, path = m.partition("=")
        if not os.path.exists(path):
            sys.exit(f"[!] missing file {path}")
        body = open(path, encoding="latin-1").read()
        http_responses += [pat, body]
        print(f"[*] http map: {pat!r} -> {path} ({len(body)} B)", file=sys.stderr)

    prelude = ("setprop(game:GetService('LocalizationService'), 'RobloxLocaleId', "
               "'%s')" % args_cli.locale)
    if args_cli.genv293:
        # the real Delta getgenv() key set (user's ==ENV== dump, Task 67)
        keys = [k.strip() for k in open(
            "samples/hermanos_env_real.txt",
            encoding="utf-8").read().split("--getgenv_sorted--")[1].split("\n")[1].split(",") if k.strip()]
        keylist = ",".join('"%s"' % k for k in keys)
        prelude += ("; local __gk = {%s}; for i=1,#__gk do "
                    "if rawget(genv, __gk[i]) == nil then "
                    "rawset(genv, __gk[i], G['getgenv'] and G['getgenv'] or "
                    "(type(G[__gk[i]])=='function' and G[__k or __gk[i]] or G[__gk[i]])) end end"
                    % keylist)
    if args_cli.prelude:
        prelude += "; " + args_cli.prelude
    pfile = "/home/z/my-project/downloads_cdn/output/locale_prelude.lua"
    os.makedirs(os.path.dirname(pfile), exist_ok=True)
    with open(pfile, "w", encoding="latin-1") as f:
        f.write(prelude)

    orig_user_cfg = harness.user_cfg

    def patched_user_cfg(args, cfg):
        orig_user_cfg(args, cfg)
        cfg["prelude"] = prelude
        cfg["heartbeat"] = int(args_cli.heartbeat)
        cfg["chunk_min"] = 512
        if not args_cli.no_flat_env:
            cfg["flat_env"] = True
        if args_cli.hide:
            cfg["env_hide"] = args_cli.hide
        for kv in args_cli.cfg:
            k, _, v = kv.partition("=")
            cfg[k] = v
        if http_responses:
            cfg["http_responses"] = list(http_responses)
        return cfg

    harness.user_cfg = patched_user_cfg

    argv = ["deob.py", INPUT,
            "--obfuscator", "luraph_v14",
            "--timeout", str(args_cli.timeout),
            "--budget", str(args_cli.budget),
            "--v14-vm-cap", str(args_cli.vmcap),
            "--v14-plain-cap", str(args_cli.plaincap),
            "--no-pypy",
            "--strings"]
    if args_cli.raw:
        argv += ["--raw", args_cli.raw]
    argv += ["-o", args_cli.out]
    sys.argv = argv

    import deob  # noqa: E402
    deob.main()


if __name__ == "__main__":
    main()
