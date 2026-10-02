"""Perturbation test for the v14.8 Cokeboys script: do the Path2D model
answers feed the VM's stage key? Compare baseline vs perturbed answers.

Signal: statements count, which loop spins, VM pc/op samples, spin start."""
import re
import subprocess
import sys
import time

sys.path.insert(0, 'deobf')
import harness

SRC = 'samples/cokeboys_v148_guarded2.lua'
LUAU = 'deobf/bin/luau'

# baseline answers captured from the model run (P2D log, tag 'model')
ANSWERS = {
    "GetLength": "n:190.6041259765625",
    "GetPositionOnCurve|0.4285714328289032": "u:0.36781936883926392,0,0.052424903959035873,0",
    "GetPositionOnCurve|0.20000000298023224": "u:0.040925931185483932,0,0.099606737494468689,0",
    "GetPositionOnCurve|0.25": "u:0.090277776122093201,0,0.090941011905670166,0",
    "GetPositionOnCurve|0.38461539149284363": "u:0.28481811285018921,0,0.063002794981002808,0",
    "GetTangentOnCurve|0.20000000298023224": "v:93.200004577636719,-14.600000381469727",
    "GetTangentOnCurve|0.2142857164144516": "v:100.85714721679688,-15.071428298950195",
    "GetPositionOnCurveArcLength|0.1666666716337204": "u:0.10620195418596268,0,0.088367722739624023,0",
    "GetPositionOnCurveArcLength|0.80000001182092896": "u:0.38621705707492554,0,0.0014671663520857692,0",
    "GetTangentOnCurveArcLength|0.3333333434750347": "v:182.3296966552734,-20.08746337890625",
    "GetTangentOnCurveArcLength|0.53846156597137451": "v:232.3629302978537,-23.167865753173828",
}


def perturb(val):
    kind, rest = val.split(":", 1)
    nums = rest.split(",")
    nums[0] = "%.17g" % (float(nums[0]) + 1.5)
    return kind + ":" + ",".join(nums)


def run(p2d, tag):
    source = open(SRC, 'rb').read().decode('latin-1')
    harness.P2D_CACHE.clear()
    harness.P2D_CACHE.update(p2d)
    cfg = {"time_budget": 90, "executor": "Wave", "heartbeat": 0}
    text = harness.build_harness(source, cfg)
    hp = '/tmp/v148_perturb_%s.luau' % tag
    open(hp, 'w', encoding='latin-1', newline='\n').write(text)
    t0 = time.time()
    try:
        r = subprocess.run([LUAU, hp], capture_output=True, timeout=140)
        out = r.stdout.decode('utf-8', 'replace')
        rc = r.returncode
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b'').decode('utf-8', 'replace')
        rc = 'TMO'
    clean = re.sub('\x00HB\r?\n {16384}\r?\n', '', out)
    m = re.search('\x00ENVLOG-BEGIN\n(.*?)\x00ENVLOG-END', clean, re.S)
    body = m.group(1) if m else ''
    stmts = re.search(r'(\d+) statements recorded', body)
    vmpcs = re.findall(r'@@VMPC (\d+) op (\d+)', body)
    spin = re.search(r'@@SPINLOOP (\d+) iter=(\d+)', body)
    p2dlog = re.findall(r'\x00P2D (\S+)', body)
    print('[%s] rc=%s elapsed=%.0fs stmts=%s vmpc_samples=%d spin=%s p2d_queries=%d' % (
        tag, rc, time.time() - t0, stmts.group(1) if stmts else '?',
        len(vmpcs), (spin.group(1) + '@' + spin.group(2)) if spin else 'none', len(p2dlog)))
    return body, vmpcs


body0, pc0 = run(ANSWERS, 'baseline')
body1, pc1 = run({k: perturb(v) for k, v in ANSWERS.items()}, 'perturbed')
print()
print('baseline pc samples (uniq):', sorted(set((a, b) for a, b in pc0))[:15])
print('perturbd pc samples (uniq):', sorted(set((a, b) for a, b in pc1))[:15])
print()
print('same spin loop?', 'yes' if (body0.find('SPINLOOP 90') >= 0) == (body1.find('SPINLOOP 90') >= 0) else 'DIFFERENT')
# how many statements before the spin in each
for tag, body in (('baseline', body0), ('perturbed', body1)):
    i = body.find('@@SPINLOOP')
    seg = body[:i] if i >= 0 else body
    print(tag, 'chars before spin:', i, 'statements lines:', seg.count('--@'))
