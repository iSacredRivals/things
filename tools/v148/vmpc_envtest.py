#!/usr/bin/env python3
"""Test de hipotesis: Random / utf8.nfcnormalize / nfdnormalize alimentan la stage key?
Perturbo cada uno via prelude y comparo la secuencia VMPC (cap 5M, ~2s por run)."""
import re
import subprocess
import sys
import time

sys.path.insert(0, 'deobf')
sys.path.insert(0, '/home/z/my-project/scripts')
import harness  # noqa: E402
from vmpc_probe import build_vmpc_source, load_real_answers  # noqa: E402

LUAU = 'deobf/bin/luau'
HP = '/home/z/my-project/scripts/vmpc_envtest.luau'

PRELUDES = {
    'random_seed+1': '''
local E = env
local rawnew = E.Random.new
E.Random = E.table.freeze({ new = function(seed)
	if E.type(seed) == "number" then seed = seed + 1 end
	return rawnew(seed)
end })
''',
    'nfc_perturb': '''
local E = env
local rawnfc = E.utf8.nfcnormalize
E.utf8.nfcnormalize = function(s)
	return rawnfc(s) .. " "
end
''',
    'nfd_perturb': '''
local E = env
local rawnfd = E.utf8.nfdnormalize
E.utf8.nfdnormalize = function(s)
	return rawnfd(s) .. " "
end
''',
}


def run(guarded, p2d, tag, prelude=None):
    harness.P2D_CACHE.clear()
    harness.P2D_CACHE.update(p2d)
    cfg = {"time_budget": 60, "executor": "Delta", "heartbeat": 0}
    if prelude:
        cfg["prelude"] = prelude
    text = harness.build_harness(guarded, cfg)
    with open(HP, 'w', encoding='latin-1', newline='\n') as f:
        f.write(text)
    t0 = time.time()
    try:
        r = subprocess.run([LUAU, HP], capture_output=True, timeout=120)
        out = r.stdout.decode('utf-8', 'replace')
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b'').decode('utf-8', 'replace')
    clean = re.sub('\x00HB\r?\n {16384}\r?\n', '', out)
    m = re.search('\x00ENVLOG-BEGIN\n(.*?)\x00ENVLOG-END', clean, re.S)
    body = m.group(1) if m else clean
    vm = re.findall(r'\[VMPC\] (\d+) pc=(\S+) op=(\S+)', body)
    stmts = re.search(r'(\d+) statements recorded', body)
    spin = re.search(r'@@SPINLOOP (\d+) iter=(\d+)', body)
    print('[%s] %.0fs stmts=%s spin=%s samples=%d' % (
        tag, time.time() - t0, stmts.group(1) if stmts else '?',
        spin.group(2) if spin else 'none', len(vm)))
    return [(int(n), pc, op) for n, pc, op in vm]


def divergence(a, b, la, lb):
    for i, ((_, p1, o1), (_, p2, o2)) in enumerate(zip(a, b)):
        if p1 != p2 or o1 != o2:
            print('  [%s vs %s] DIVERGE sample %d: %s/%s | %s/%s' % (la, lb, i, p1, o1, p2, o2))
            print('    A: ' + ' '.join('%s/%s' % (p, o) for _, p, o in a[max(0, i - 5):i + 8]))
            print('    B: ' + ' '.join('%s/%s' % (p, o) for _, p, o in b[max(0, i - 5):i + 8]))
            return
    print('  [%s vs %s] IDENTICAS (%d muestras)' % (la, lb, min(len(a), len(b))))


def main():
    guarded = build_vmpc_source()
    real = load_real_answers()
    base = run(guarded, real, 'base')
    print()
    for name, pre in PRELUDES.items():
        seq = run(guarded, real, name, pre)
        divergence(base, seq, 'base', name)
        print()


if __name__ == '__main__':
    main()
