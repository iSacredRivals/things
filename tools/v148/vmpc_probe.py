#!/usr/bin/env python3
"""Sonda VMPC para el VM v14.8 del Cokeboys: inyecta logging (pc, opcode) en el
dispatcher y compara la ejecucion con respuestas P2D reales vs modelo.

La divergencia entre ambas secuencias localiza la comparacion de la stage key;
el mapa de opcodes de la suite (luraph_14_8_opcodes.json) traduce los ops.
"""
import re
import subprocess
import sys
import time

sys.path.insert(0, 'deobf')
import harness  # noqa: E402
from obfuscators.luraph_v14 import guards  # noqa: E402

SRC_PATH = 'samples/cokeboys_v148.lua'
LUAU = 'deobf/bin/luau'
HP = '/home/z/my-project/scripts/vmpc_harness.luau'
OPCODES_JSON = '/home/z/my-project/v148_suite/datasets/luraph_14_8_opcodes.json'
VM_CAP = 5_000_000

# respuestas del modelo (baseline de perturb_v148.py; los tangentes difieren de las reales)
MODEL_ANSWERS = {
    "GetLength": "n:190.6041259765625",
    "GetPositionOnCurve|0.4285714328289032": "u:0.36781936883926392,0,0.052424903959035873,0",
    "GetPositionOnCurve|0.20000000298023224": "u:0.040925931185483932,0,0.099606737494468689,0",
    "GetPositionOnCurve|0.25": "u:0.090277776122093201,0,0.090941011905670166,0",
    "GetPositionOnCurve|0.38461539149284363": "u:0.28481811285018921,0,0.063002794981002808,0",
    "GetTangentOnCurve|0.20000000298023224": "v:93.200004577636719,-14.600000381469727",
    "GetTangentOnCurve|0.2142857164144516": "v:100.85714721679688,-15.071428298950195",
    "GetPositionOnCurveArcLength|0.1666666716337204": "u:0.10620195418596268,0,0.088367223739624023,0",
    "GetPositionOnCurveArcLength|0.80000001192092896": "u:0.38621705770492554,0,0.0014671663520857692,0",
    "GetTangentOnCurveArcLength|0.3333333432674408": "v:182.3296966552734,-20.08746337890625",
    "GetTangentOnCurveArcLength|0.53846156597137451": "v:232.3629302978537,-23.167865753173828",
}


def load_real_answers():
    real = {}
    for line in open('samples/cokeboys_v148.path2d', encoding='utf-8'):
        k, _, v = line.rstrip('\n').partition('\t')
        if k:
            real[k] = v
    return real


VMPC_PRELUDE = '''local __VMPCN = 0
local function __VMPC(pc, op)
        __VMPCN = __VMPCN + 1
        if __VMPCN <= 600 or __VMPCN % 50000 == 0 then
                print("[VMPC] " .. tostring(__VMPCN) .. " pc=" .. tostring(pc) .. " op=" .. tostring(op))
        end
end
'''


def build_vmpc_source():
    src = open(SRC_PATH, 'rb').read().decode('latin-1')
    guarded, n_loops, n_vm = guards.inject(src, VM_CAP, 5_000_000)
    print('[*] loops guarded: %d (VM: %d)' % (n_loops, n_vm))
    # el fetch del dispatcher: __LC[NN](); local i=(F[x]);
    m = re.search(r'__LC\[(\d+)\]\(\);\s*local\s+(\w+)\s*=\s*\(?\s*(\w+)\s*\[\s*(\w+)\s*\]\s*\)?\s*;',
                  guarded)
    if not m:
        sys.exit('[!] no encontre el fetch del dispatcher en el fuente guardado')
    var, arr, idx = m.group(2), m.group(3), m.group(4)
    print('[*] dispatcher: loop %s, fetch local %s=(%s[%s])' % (m.group(1), var, arr, idx))
    guarded = guarded[:m.end()] + ' __VMPC(%s, %s);' % (idx, var) + guarded[m.end():]
    # prelude VMPC tras la cabecera (como guards)
    head = re.match(r'(--[^\n]*\n)', guarded)
    h = head.group(1) if head else ''
    guarded = h + '\n' + VMPC_PRELUDE + guarded[len(h):]
    return guarded


def run(guarded, p2d, tag):
    harness.P2D_CACHE.clear()
    harness.P2D_CACHE.update(p2d)
    cfg = {"time_budget": 90, "executor": "Delta", "heartbeat": 0}
    text = harness.build_harness(guarded, cfg)
    with open(HP, 'w', encoding='latin-1', newline='\n') as f:
        f.write(text)
    t0 = time.time()
    try:
        r = subprocess.run([LUAU, HP], capture_output=True, timeout=180)
        out = r.stdout.decode('utf-8', 'replace')
        rc = r.returncode
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b'').decode('utf-8', 'replace')
        rc = 'TMO'
    clean = re.sub('\x00HB\r?\n {16384}\r?\n', '', out)
    m = re.search('\x00ENVLOG-BEGIN\n(.*?)\x00ENVLOG-END', clean, re.S)
    body = m.group(1) if m else clean
    vm = re.findall(r'\[VMPC\] (\d+) pc=(\S+) op=(\S+)', body)
    stmts = re.search(r'(\d+) statements recorded', body)
    spin = re.search(r'@@SPINLOOP (\d+) iter=(\d+)', body)
    print('[%s] rc=%s %.0fs stmts=%s spin=%s vmpc_samples=%d' % (
        tag, rc, time.time() - t0, stmts.group(1) if stmts else '?',
        (spin.group(1) + '@' + spin.group(2)) if spin else 'none', len(vm)))
    return [(int(n), pc, op) for n, pc, op in vm]


def main():
    guarded = build_vmpc_source()
    real = load_real_answers()
    seq_real = run(guarded, real, 'real')
    seq_model = run(guarded, MODEL_ANSWERS, 'model')

    # primeros 80 pasos de cada
    print()
    print('=== primeros 60 (real) ===')
    print(' '.join('%s/%s' % (pc, op) for _, pc, op in seq_real[:60]))
    print('=== primeros 60 (model) ===')
    print(' '.join('%s/%s' % (pc, op) for _, pc, op in seq_model[:60]))
    # divergencia
    print()
    n = 0
    for i, ((_, pc_r, op_r), (_, pc_m, op_m)) in enumerate(zip(seq_real, seq_model)):
        if pc_r != pc_m or op_r != op_m:
            n = i
            print('[*] DIVERGENCIA en sample %d (iter %s): real pc=%s op=%s | model pc=%s op=%s' % (
                i, seq_real[i][0], pc_r, op_r, pc_m, op_m))
            print('    contexto real : ' + ' '.join('%s/%s' % (p, o) for _, p, o in seq_real[max(0, i - 6):i + 10]))
            print('    contexto model: ' + ' '.join('%s/%s' % (p, o) for _, p, o in seq_model[max(0, i - 6):i + 10]))
            break
    if n == 0 and seq_real[:len(seq_model)] == seq_model[:len(seq_real)]:
        print('[*] secuencias identicas (en las muestras capturadas)')
    print()
    print('=== steady state real (ultimas 12 muestras) ===')
    print(' '.join('%s/%s' % (pc, op) for _, pc, op in seq_real[-12:]))
    print('=== steady state model (ultimas 12) ===')
    print(' '.join('%s/%s' % (pc, op) for _, pc, op in seq_model[-12:]))
    # persistir
    with open('/home/z/my-project/scripts/vmpc_real.txt', 'w') as f:
        f.write('\n'.join('%d\t%s\t%s' % t for t in seq_real))
    with open('/home/z/my-project/scripts/vmpc_model.txt', 'w') as f:
        f.write('\n'.join('%d\t%s\t%s' % t for t in seq_model))
    print('[+] persistidos vmpc_real.txt / vmpc_model.txt')


if __name__ == '__main__':
    main()
