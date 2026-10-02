#!/usr/bin/env python3
"""Driver for obf_3.lua (Luraph v15.0, AteneaNyx/DevAurora-Scripts).

Runs the engine's luraph_v15 pipeline with:
  - http_responses injection (the real pastefy body "839271", plus any
    extra url=body maps from --map) so the loader proceeds past its
    remote version/check gate;
  - optional --no-devirt for the fast behaviour trace.

Usage:
  python3 run_obf3_v15.py [--no-devirt] [--map "url-substr=path"]* [--out OUT]
"""
import argparse
import os
import sys

ENGINE = "deobf"
sys.path.insert(0, ENGINE)
os.chdir(ENGINE)

import harness  # noqa: E402

INPUT = "/home/z/my-project/downloads_cdn/obf_3.lua"
OUT = "/home/z/my-project/downloads_cdn/output/obf_3.luau"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-devirt", action="store_true")
    ap.add_argument("--map", action="append", default=[],
                    help="extra http_responses pair url-substr=path (repeatable)")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--timeout", type=int, default=240)
    ap.add_argument("--budget", type=int, default=120)
    ap.add_argument("--prelude", default=None,
                    help="prelude code (runs first, sets globals/props)")
    args_cli = ap.parse_args()

    # ---- http_responses the loader will see ------------------------------
    http_responses = ["LPwtBxk4", "839271"]     # the real pastefy body
    for m in args_cli.map:
        pat, _, path = m.partition("=")
        if not os.path.exists(path):
            sys.exit(f"[!] missing file {path}")
        body = open(path, encoding="latin-1").read()
        http_responses += [pat, body]
        print(f"[*] http map: {pat!r} -> {path} ({len(body)} B)", file=sys.stderr)

    # ---- patch harness so every cfg gets our http_responses --------------
    orig_user_cfg = harness.user_cfg

    def patched_user_cfg(args, cfg):
        orig_user_cfg(args, cfg)
        cfg["http_responses"] = list(http_responses)

    harness.user_cfg = patched_user_cfg

    # ---- build argv and run deob.py's main -------------------------------
    argv = ["deob.py", INPUT,
            "--obfuscator", "luraph_v15",
            "--timeout", str(args_cli.timeout),
            "--budget", str(args_cli.budget),
            "--no-pypy",
            "-o", args_cli.out,
            "--strings"]
    if args_cli.no_devirt:
        argv.append("--no-devirt")
    if args_cli.prelude:
        # long/quoted prelude code goes through a file (@file: support)
        pfile = "/home/z/my-project/downloads_cdn/output/prelude_snippet.lua"
        os.makedirs(os.path.dirname(pfile), exist_ok=True)
        with open(pfile, "w", encoding="latin-1") as f:
            f.write(args_cli.prelude)
        argv += ["--cfg", "prelude=@file:" + pfile]
    sys.argv = argv

    import deob  # noqa: E402  (imports after the patch: driver uses our harness)
    deob.main()


if __name__ == "__main__":
    main()
