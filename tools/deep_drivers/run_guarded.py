"""Build an envlog harness around the loop-guarded v14.8 script and run it,
to find which loop spins forever."""
import sys
import time

sys.path.insert(0, 'deobf')
import harness

SRC = 'samples/cokeboys_v148_guarded.lua'
OUT = '/tmp/v148_guarded_harness.luau'

source = open(SRC, 'rb').read().decode('latin-1')
cfg = {"time_budget": 120, "executor": "Wave", "heartbeat": 2}
text = harness.build_harness(source, cfg)
open(OUT, 'w', encoding='latin-1', newline='\n').write(text)
print('harness:', OUT, len(text), 'bytes')

import subprocess
t0 = time.time()
try:
    r = subprocess.run(['deobf/bin/luau', OUT],
                       capture_output=True, timeout=250)
    out = r.stdout.decode('utf-8', 'replace')
    err = r.stderr.decode('utf-8', 'replace')
    print('rc:', r.returncode, 'elapsed: %.1fs' % (time.time() - t0))
    print('stdout size:', len(out))
    # strip heartbeat padding
    import re
    clean = re.sub(r'\x00HB\r?\n {16384}\r?\n', '', out)
    print('clean stdout size:', len(clean))
    idx = clean.find('@@SPINLOOP')
    print('STUCKLOOP at:', idx)
    if idx >= 0:
        print('==== around STUCKLOOP:')
        print(clean[idx:idx + 400])
    print('==== tail of clean stdout:')
    print(clean[-1500:])
    print('==== stderr:')
    print(err[:800])
except subprocess.TimeoutExpired as e:
    print('TIMEOUT after %.1fs' % (time.time() - t0))
    out = (e.stdout or b'').decode('utf-8', 'replace')
    import re
    clean = re.sub(r'\x00HB\r?\n {16384}\r?\n', '', out)
    idx = clean.find('@@SPINLOOP')
    print('STUCKLOOP at:', idx)
    print(clean[:600] if idx < 0 else clean[idx:idx + 400])
    print('==== tail:')
    print(clean[-600:])
