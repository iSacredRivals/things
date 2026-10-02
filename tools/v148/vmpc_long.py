#!/usr/bin/env python3
"""Run largo del VM v14.8: cap 5B, VMPC cada 10M iteraciones, streaming.
Objetivo: ver si el decode del dispatcher termina y a donde va el VM despues."""
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
HP = '/home/z/my-project/scripts/vmpc_long.luau'
CAP = 5_000_000_000

VMPC_PRELUDE = '''local __VMPCN = 0
local function __VMPC(pc, op)
        __VMPCN = __VMPCN + 1
        if __VMPCN % 10000000 == 0 then
                print("[VMPC] " .. __VMPCN .. " pc=" .. tostring(pc) .. " op=" .. tostring(op))
        end
end
'''


def load_real_answers():
    real = {}
    for line in open('samples/cokeboys_v148.path2d', encoding='utf-8'):
        k, _, v = line.rstrip('\n').partition('\t')
        if k:
            real[k] = v
    return real


def build():
    src = open(SRC_PATH, 'rb').read().decode('latin-1')
    guarded, n_loops, n_vm = guards.inject(src, CAP, 5_000_000)
    print('[*] loops: %d (VM: %d), cap %d' % (n_loops, n_vm, CAP))
    m = re.search(r'__LC\[(\d+)\]\(\);\s*local\s+(\w+)\s*=\s*\(?\s*(\w+)\s*\[\s*(\w+)\s*\]\s*\)?\s*;',
                  guarded)
    if not m:
        sys.exit('[!] fetch no encontrado')
    var, idx = m.group(2), m.group(4)
    guarded = guarded[:m.end()] + ' __VMPC(%s, %s);' % (idx, var) + guarded[m.end():]
    head = re.match(r'(--[^\n]*\n)', guarded)
    h = head.group(1) if head else ''
    guarded = h + '\n' + VMPC_PRELUDE + guarded[len(h):]
    return guarded


def main():
    guarded = build()
    harness.P2D_CACHE.clear()
    harness.P2D_CACHE.update(load_real_answers())
    cfg = {"time_budget": 3000, "executor": "Delta", "heartbeat": 0}
    text = harness.build_harness(guarded, cfg)
    with open(HP, 'w', encoding='latin-1', newline='\n') as f:
        f.write(text)
    print('[*] harness listo (%.1f MB), lanzando luau bajo PTY (line-buffered)...' % (len(text) / 1e6))
    t0 = time.time()
    inner = '%s %s' % (LUAU, HP)
    proc = subprocess.Popen(['script', '-qec', inner, '/dev/null'],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            start_new_session=True)
    n_vm = 0
    n_other = 0
    logf = open('/home/z/my-project/scripts/vmpc_long_stream.log', 'w', buffering=1)
    try:
        for raw in proc.stdout:
            line = raw.decode('utf-8', 'replace').replace('\r', '').rstrip()
            if '[VMPC]' in line:
                n_vm += 1
                msg = '%7.0fs %s' % (time.time() - t0, line[:100])
                print(msg)
                logf.write(msg + '\n')
            elif line:
                n_other += 1
                if n_other % 800 == 0:
                    msg = '%7.0fs ... (+%d lineas de actividad)' % (time.time() - t0, n_other)
                    print(msg)
                    logf.write(msg + '\n')
            if 'SPINLOOP' in line or 'run status' in line or 'statements recorded' in line:
                msg = '%7.0fs >>> %s' % (time.time() - t0, line[:160])
                print(msg)
                logf.write(msg + '\n')
            if time.time() - t0 > 500:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except Exception:
                    proc.kill()
                print('[!] timeout local 500s - matando grupo')
                logf.write('[!] timeout local 500s\n')
                break
    finally:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:
            proc.kill()
        logf.close()
    print('[*] muestras VMPC: %d, otras lineas: %d, total %.0fs' % (n_vm, n_other, time.time() - t0))


if __name__ == '__main__':
    main()
