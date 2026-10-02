#!/usr/bin/env python3
"""Run FINAL lean: sin guard en loop 90, sin dumper, --codegen, heartbeat=2.
Exit antes de 560s = decode completo (trace+strings flush-ean)."""
import os
import re
import signal
import subprocess
import sys
import time

sys.path.insert(0, 'deobf')
sys.path.insert(0, '/home/z/my-project/scripts')
import harness  # noqa: E402
from obfuscators.luraph_v14 import guards  # noqa: E402

SRC_PATH = 'samples/cokeboys_v148.lua'
LUAU = 'deobf/bin/luau'
HP = '/home/z/my-project/scripts/vmpc_final.luau'


def load_real_answers():
    real = {}
    for line in open('samples/cokeboys_v148.path2d', encoding='utf-8'):
        k, _, v = line.rstrip('\n').partition('\t')
        if k:
            real[k] = v
    return real


def main():
    src = open(SRC_PATH, 'rb').read().decode('latin-1')
    guarded, n_loops, n_vm = guards.inject(src, 5_000_000_000, 5_000_000)
    # quitar el guard del dispatcher (overhead por iteracion)
    m = re.search(r'__LC\[(\d+)\]\(\);\s*local\s+(\w+)\s*=\s*\(?\s*(\w+)\s*\[\s*(\w+)\s*\]\s*\)?\s*;',
                  guarded)
    loop_id = m.group(1)
    print('[*] dispatcher loop %s: quitando guard para maxima velocidad' % loop_id)
    guarded = guarded.replace(' __LC[%s]();' % loop_id, '', 1)
    if ' __LC[%s]();' % loop_id in guarded:
        sys.exit('[!] no se pudo quitar el guard')
    harness.P2D_CACHE.clear()
    harness.P2D_CACHE.update(load_real_answers())
    cfg = {"time_budget": 3000, "executor": "Delta", "heartbeat": 2, "dump_strings": True}
    text = harness.build_harness(guarded, cfg)
    with open(HP, 'w', encoding='latin-1', newline='\n') as f:
        f.write(text)
    print('[*] harness lean listo (%.1f MB), luau --codegen...' % (len(text) / 1e6))
    t0 = time.time()
    proc = subprocess.Popen([LUAU, '--codegen', HP], stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, start_new_session=True)
    logf = open('/home/z/my-project/scripts/vmpc_final.log', 'wb')
    n_hb = 0
    n_stmt = 0
    exited = False
    try:
        for raw in proc.stdout:
            logf.write(raw)
            line = raw.decode('utf-8', 'replace')
            if line.startswith('\x00HB'):
                n_hb += 1
                if n_hb % 25 == 0:
                    print('%6.0fs ... vivo (HB %d)' % (time.time() - t0, n_hb))
            elif 'statements recorded' in line or 'run status' in line:
                n_stmt += 1
                print('%6.0fs >>> %s' % (time.time() - t0, line.rstrip()[:120]))
            if time.time() - t0 > 555:
                break
    finally:
        if proc.poll() is None:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except Exception:
                proc.kill()
        else:
            exited = True
        logf.close()
    print('[*] exited=%s HBs=%d stmts=%d total %.0fs' % (exited, n_hb, n_stmt, time.time() - t0))


if __name__ == '__main__':
    main()
