#!/usr/bin/env python3
"""Diferencial VMPC: que entradas alimentan el flujo del VM v14.8?
Variantes: real / perturb(+1.5 P2D) / executor Wave / tangentes ULP-off.
La que diverge la secuencia = alimenta la clave."""
import re
import subprocess
import sys
import time

sys.path.insert(0, 'deobf')
sys.path.insert(0, '/home/z/my-project/scripts')
import harness  # noqa: E402
from vmpc_probe import build_vmpc_source, load_real_answers, MODEL_ANSWERS  # noqa: E402

LUAU = 'deobf/bin/luau'
HP = '/home/z/my-project/scripts/vmpc_harness2.luau'


def perturb(d, delta=1.5):
    out = {}
    for k, v in d.items():
        kind, rest = v.split(":", 1)
        nums = rest.split(",")
        nums[0] = "%.17g" % (float(nums[0]) + delta)
        out[k] = kind + ":" + ",".join(nums)
    return out


def perturb_tangents_only(d):
    out = dict(d)
    for k, v in d.items():
        if k.startswith("GetTangent"):
            kind, rest = v.split(":", 1)
            nums = rest.split(",")
            nums[0] = "%.17g" % (float(nums[0]) * (1 + 1e-13))
            out[k] = kind + ":" + ",".join(nums)
    return out


def run(guarded, p2d, tag, executor="Delta"):
    harness.P2D_CACHE.clear()
    harness.P2D_CACHE.update(p2d)
    cfg = {"time_budget": 60, "executor": executor, "heartbeat": 0}
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
            print('  [%s vs %s] DIVERGE sample %d: %s/%s | %s/%s' % (
                la, lb, i, p1, o1, p2, o2))
            print('    A: ' + ' '.join('%s/%s' % (p, o) for _, p, o in a[max(0, i - 5):i + 8]))
            print('    B: ' + ' '.join('%s/%s' % (p, o) for _, p, o in b[max(0, i - 5):i + 8]))
            return i
    print('  [%s vs %s] IDENTICAS (%d muestras)' % (la, lb, min(len(a), len(b))))
    return -1


def main():
    guarded = build_vmpc_source()
    real = load_real_answers()
    base = run(guarded, real, 'real')

    print()
    v_perturb = run(guarded, perturb(real), 'perturb+1.5')
    print()
    v_exec = run(guarded, real, 'executorWave', executor="Wave")
    print()
    v_tang = run(guarded, perturb_tangents_only(real), 'tangentsULP')

    print()
    print('=== DIVERGENCIAS ===')
    divergence(base, v_perturb, 'real', 'perturb')
    divergence(base, v_exec, 'real', 'execWave')
    divergence(base, v_tang, 'real', 'tangULP')


if __name__ == '__main__':
    main()
