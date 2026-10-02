#!/usr/bin/env python3
"""Dumper de estado del VM v14.8 v2: la funcion de dump vive a nivel CHUNK
(el env del VM esta setfenveado y no tiene print); el loop solo la llama."""
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
HP = '/home/z/my-project/scripts/vmpc_state2.luau'
CAP = 400_000_000
INTERVAL = 100000000

DUMP_PRELUDE = '''local __STN = 0
local __tstr, __srep = tostring, string.rep
local function __STDUMP(x, X, U, B, b, S)
        __STN = __STN + 1
        if __STN %% %d == 0 then
                local ok, err = pcall(function()
                        print("[ST] n=" .. __STN .. " x=" .. __tstr(x) .. " X28=" .. __tstr(X[28]) .. " X38=" .. __tstr(X[38])
                                .. " U=" .. __tstr(U[1]) .. "," .. __tstr(U[2]) .. "," .. __tstr(U[3]) .. "," .. __tstr(U[5])
                                .. "," .. __tstr(U[7]) .. "," .. __tstr(U[11])
                                .. " B=" .. __tstr(B) .. " b=" .. __tstr(b) .. " S=" .. __tstr(S) .. __srep(" ", 9000))
                end)
                if not ok then print("[STERR] " .. __tstr(err) .. __srep(" ", 9000)) end
        end
end
''' % INTERVAL

CALL_INJECT = ' __STDUMP(x, X, U, B, b, S);'


def load_real_answers():
    real = {}
    for line in open('samples/cokeboys_v148.path2d', encoding='utf-8'):
        k, _, v = line.rstrip('\n').partition('\t')
        if k:
            real[k] = v
    return real


def main():
    src = open(SRC_PATH, 'rb').read().decode('latin-1')
    guarded, n_loops, n_vm = guards.inject(src, CAP, 5_000_000)
    m = re.search(r'__LC\[(\d+)\]\(\);\s*local\s+(\w+)\s*=\s*\(?\s*(\w+)\s*\[\s*(\w+)\s*\]\s*\)?\s*;',
                  guarded)
    if not m:
        sys.exit('[!] fetch no encontrado')
    guarded = guarded[:m.end()] + CALL_INJECT + guarded[m.end():]
    head = re.match(r'(--[^\n]*\n)', guarded)
    h = head.group(1) if head else ''
    guarded = h + '\n' + DUMP_PRELUDE + guarded[len(h):]
    harness.P2D_CACHE.clear()
    harness.P2D_CACHE.update(load_real_answers())
    cfg = {"time_budget": 3000, "executor": "Delta", "heartbeat": 0, "dump_strings": True}
    text = harness.build_harness(guarded, cfg)
    with open(HP, 'w', encoding='latin-1', newline='\n') as f:
        f.write(text)
    print('[*] harness listo (%.1f MB), lanzando...' % (len(text) / 1e6))
    t0 = time.time()
    proc = subprocess.Popen([LUAU, HP], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            start_new_session=True)
    logf = open('/home/z/my-project/scripts/vmpc_state.log', 'w', buffering=1)
    n = 0
    try:
        for raw in proc.stdout:
            line = raw.decode('utf-8', 'replace').replace('\r', '').rstrip()
            if '[ST]' in line or 'SPINLOOP' in line or 'statements' in line:
                n += 1
                msg = '%6.0fs %s' % (time.time() - t0, line[:200])
                print(msg)
                logf.write(msg + '\n')
            if time.time() - t0 > 555:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except Exception:
                    proc.kill()
                print('[!] timeout 540s')
                logf.write('[!] timeout 540s\n')
                break
    finally:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:
            proc.kill()
        logf.close()
    print('[*] lineas de estado: %d, total %.0fs' % (n, time.time() - t0))


if __name__ == '__main__':
    main()
