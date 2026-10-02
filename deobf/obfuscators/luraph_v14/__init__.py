"""Luraph v14.8 plugin: behaviour trace with loop guards (notes: LURAPH_V14.md).

v14.8 is not a pure VM like v15: the script keeps most of its logic as plain
(albeit mangled) Luau - mixed-escape strings, env-array indirection, phase
machines - plus one `[==[LPH...]==]` ASCII85 payload whose decoded constants
are gated behind a stage key derived from live engine values (Path2D curve
answers on the Cokeboys sample). The plugin traces the script in the
instrumented VM like `generic`, but with two v14 additions:

* loop guards (guards.py): a wrong stage key makes the VM's decode loop spin
  in pure bytecode without touching the environment, where the time budget
  never fires; the guards bound every loop and turn the spin into a clean
  abort that keeps the trace gathered so far;
* a Path2D spin diagnosis: when a VM loop hits its cap the result explains
  the cause and points at the recorder workflow (record the real answers in
  a client, replay them here).
"""
import re
import sys

import harness
import traceout as trace
from obfuscators.base import Obfuscator

HEADER = re.compile(r"This file was protected using Luraph Obfuscator v(\d+)\.(\d+)")
LPH_BRACKET = re.compile(r"\[(=+)\[LPH")
HEADER_LINE = re.compile(r"\s*--[ \t]*This file was protected using Luraph Obfuscator v[\d.]+[ \t]*"
                         r"[ht]?tps://lura\.ph/?\]")


class LuraphV14(Obfuscator):
    name = "luraph_v14"
    label = "Luraph v14.8"
    doc = "LURAPH_V14.md"

    def detect(self, source):
        m = HEADER.search(source[:600])
        if m:
            return 1.0 if m.group(1) == "14" else 0.3     # family, not verified
        # header stripped: the v14 payload long bracket is a strong marker
        if LPH_BRACKET.search(source[:300000]):
            return 0.85
        return 0.0

    def add_arguments(self, ap):
        g = ap.add_argument_group("Luraph v14.8")
        g.add_argument("--v14-vm-cap", type=int, default=250_000_000,
                       help="iteration cap for VM dispatch loops (default 250M; they legitimately "
                            "run millions of instructions)")
        g.add_argument("--v14-plain-cap", type=int, default=50_000_000,
                       help="iteration cap for ordinary while/repeat loops (default 50M; the v14.8 "
                            "payload decode itself is a plain state-machine loop)")
        g.add_argument("--v14-spin-seconds", type=int, default=0,
                       help="abort a loop still running after this many seconds (0 = auto: the time "
                            "budget, min 60; pure-compute decode phases never emit, so only the "
                            "guard can bound them)")

    def deobfuscate(self, job):
        from obfuscators.luraph_v14 import guards
        args = job.args
        source = restore_header_newline(job.source)
        if source != job.source:
            print("[*] header comment ran into the code (lost newline): split it", file=sys.stderr)
            job.source = source
        spin = args.v14_spin_seconds or max(args.budget, 60)
        guarded, n_loops, n_vm = guards.inject(source, args.v14_vm_cap, args.v14_plain_cap, spin)
        if n_loops:
            print("[*] %d loops guarded (%d VM dispatch loops): caps + %ds spin bound; hot loops "
                  "throttle their own emissions" % (n_loops, n_vm, spin), file=sys.stderr)

        cache_path = harness.load_p2d_cache(job.input, args.studio)
        runner = harness.Runner(job)
        cfg = harness.user_cfg(args, harness.base_cfg(args))
        # pure-compute phases are normal in v14 (payload decode); the guards,
        # not the output stall detector, bound them
        cfg.setdefault("heartbeat", 0)
        # time spent with a hot loop's emissions throttled does not count
        # against the budget: --budget bounds traced behaviour, the spin bound
        # bounds the whole run
        cfg["vm_pause"] = True
        if args.strings:
            cfg["dump_strings"] = True
        print("[*] tracing %s..." % job.input, file=sys.stderr)
        body, err = runner.run(guarded, cfg)
        if body is None:
            harness.save_raw(args.raw)
            runner.finish()
            sys.exit("[!] " + err)
        runner.finish()
        harness.save_raw(args.raw)
        body = harness.take_p2d(body, cache_path, args.studio)
        body = harness.p2d_miss(body, cache_path)
        chunks, body = harness.take_chunks(body)
        if chunks:
            # layered v14 scripts loadstring their next stage: keep it (it is a
            # result of its own - re-run deob.py on it)
            import os
            import shutil
            outdir = os.path.join(os.path.dirname(os.path.abspath(job.input)), "output")
            os.makedirs(outdir, exist_ok=True)
            for key, src in chunks:
                cpath = job.write(job.path(".chunk_%s.lua" % key), src, encoding="latin-1")
                if not job.debug:
                    # the work dir dies with the temp folder: keep a copy next
                    # to the result file
                    final = os.path.join(outdir, os.path.basename(job.input) + ".chunk_%s.lua" % key)
                    shutil.copyfile(cpath, final)
                    cpath = final
                print("[+] loadstring'd chunk: " + cpath, file=sys.stderr)
        body, strings = trace.take_strings(body)
        body, spin_ids = guards.strip_spin_markers(body)
        notes = []
        if spin_ids:
            notes.append("loop(s) %s hit the guard (iteration cap or %ds time bound): a wrong stage "
                         "key decode loops forever" % (", ".join(spin_ids), spin))
            notes.append("the Path2D answers of the offline model are not bit-exact with a real "
                         "client; record them and replay (see LURAPH_V14.md), or the loop needs "
                         "more time than the spin bound (--v14-spin-seconds)")
            print("[!] loop(s) %s hit the guard: the stage key did not decode (Path2D answers "
                  "needed - see the notes in the result)" % ", ".join(spin_ids), file=sys.stderr)
        text = trace.render(job.credit_header() + trace.header(job.input, notes) + body, args)
        job.write(job.trace_path, text)
        if strings is not None:
            job.write(job.path(".strings.txt"), strings)
            if not job.debug:
                # the work dir is deleted after the run: keep a copy next to
                # the result file so --strings is useful in the default flow
                import os
                import shutil
                outdir = os.path.join(os.path.dirname(os.path.abspath(job.input)), "output")
                final = os.path.join(outdir, os.path.basename(job.input) + ".strings.txt")
                os.makedirs(outdir, exist_ok=True)
                shutil.copyfile(job.path(".strings.txt"), final)
                print("[+] strings: " + final, file=sys.stderr)
        trace.status_line(body)
        return job.trace_path


def restore_header_newline(source):
    """Pasted copies can lose the newline after the `-- This file was
    protected ...` line (the whole script becomes that comment). Put it back.
    Tolerates the `[h` the paste sometimes eats from `[https://lura.ph/]`."""
    m = HEADER_LINE.match(source)
    if m and source[m.end():m.end() + 1] not in ("", "\n", "\r"):
        return source[:m.end()] + "\n" + source[m.end():].lstrip(" \t")
    return source
