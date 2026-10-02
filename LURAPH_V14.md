# luraph v14.8 (`deobf/obfuscators/luraph_v14/`)

> Reference, not changelog (same rules as CLAUDE.md). **Hard limit: 500 lines.**

Header `-- This file was protected using Luraph Obfuscator v14.8 [https://lura.ph/]`
(pasted copies can lose the `[h` and/or the newline; detect tolerates both).
Status: **behaviour trace + loop guards (caps, spin bound, trace throttle) +
string capture + chunk capture**. Full devirtualization of the VM sections is
future work (see "Lifting" below).

## Samples

| Sample | What it is | Result (plain run) |
|---|---|---|
| `samples/cokeboys_v148.lua` | Cokeboys Blox Fruits V1.8 (2.7 MB, `message.txt` from Discord) | 154-statement trace (decoy UI + probes + services), 167 decrypted strings; VM decode still blocked by the Path2D stage key: loop 90 aborts at the spin bound with the recorder workflow in the notes |
| `samples/v148_hot_loop_test.lua` | synthetic: hot loop that emits per iteration | 200k iterations, `finished`: the first 25k statements in the (folded) block, a continuation block with everything after the loop - no truncation, no abort |

## What v14.8 is (vs v15)

Not a pure VM. The script is *plain mangled Luau* plus a compressed payload:

* most logic stays as ordinary functions: mixed-escape strings
  (`\x4C\u{61}\z...`), env-array indirection (`R[3][R[2]]` aliasing upvalues),
  numeric mazes (`(-3926726801+(R.Wq(...)))`), phase machines
  (`while o do G,q=R:PK(q,X,c,n); if G==0X7F9E then break`) - all of that
  resolves *at run time*, which is exactly what the behaviour trace records;
* one `[==[LPH...]==]` long bracket (1.6 MB here) - the constants payload,
  ASCII85-ish decoded into a 1.28 MB LE-u32 buffer *inside the script*;
  decoding it statically (suite's `payload_extractor.py` approach) yields
  garbage: the readable constants only appear after the VM's own
  multi-stage decode, which is **key-gated**;
* the VM interpreter(s) sit near the end of the file: `while true do
  local i=(F[x]); if not(i<289)then ... ` - a **binary-search if-chain**
  over the opcode, operands in parallel arrays (`p/t/H/y/A` indexed by pc
  `x`), registers in `U`. Note the **parenthesized fetch** `local i=(F[x])`
  (an `AstExprGroup`): luraph_v15's `vmmap.find_dispatchers` rejects it as-is.

## The stage key and why runs spin (root cause)

Same design as the v15 sample `deobf_pls.lua`: before the VM's decode phase
the script builds a ScreenGui + Frame + `Path2D` with 3 control points and
queries the curve (`GetLength`, `GetPositionOnCurve|t`, `GetTangentOnCurve|t`,
`*ArcLength` variants - 12 calls here). The answers are hashed into the
decode key. The offline engine model answers all of them (self-consistent,
bit-exact with its own float32 model) but is **not bit-exact with a real
client**, so the key is wrong; the decode then either spins forever in pure
bytecode (cokeboys: no environment access, so `checkBudget` - which fires on
emit - never triggers) or computes a garbage buffer size and dies at
`buffer.create` (obf_4, the Luarmor bootstrapper).

Verified on both samples: perturbing any P2D answer changes the VM's control
flow (different statements, different error) - the answers are genuinely
data-dependent, not decoration.

## Pipeline (`__init__.py`)

1. `restore_header_newline`: put the newline back after the header comment if
   the paste lost it (v15's fix, tolerating the eaten `[h`).
2. `guards.inject` (AST-based via `luauast`): a counter at the head of
   **every** while/repeat loop - `__LC[n].c+=1;if __LC[n].c>=4096 then
   __LC.f(n)end;`, TABLE OPERATIONS ONLY (a call per iteration would add a
   stack frame, and Luraph mixes stack depth into its probes; no new locals
   in the loop body either). `__LC.f(n)` (every 4096 iterations) checks:
   * the iteration cap: VM dispatch loops (opcode fetch right at the head,
     `--v14-vm-cap`, default 250M) vs everything else (`--v14-plain-cap`,
     default 50M - the v14.8 payload decode itself is a plain state machine);
   * the time bound (`--v14-spin-seconds`, 0 = auto: max(budget, 60)): pure
     compute never emits, so the emit-based budget cannot see those phases -
     the guard is what bounds them;
   * `__VMBEAT`: keeps the tracer's block-full silence alive while the loop
     runs (see the throttle below).
   A loop that crosses a bound errors with `@@SPINLOOP <n>`: envlog reports
   it like any script error, the trace gathered so far is dumped, and the
   plugin turns the marker into NOTE lines pointing at the recorder workflow.
   `__LC.r(n)` is injected after each guarded loop's `end` and re-arms
   tracing when the loop exits.
3. **Guard prelude placement (the obf_4 bug)**: the prelude is inserted at
   the first top-level statement's offset (AST-located), i.e. *after every
   leading comment*. obf_4 starts with a `--[[ Luarmor V4 bootstrapper ]]`
   block comment that used to swallow the whole prelude: `__LC` then resolved
   as an unknown GLOBAL - the fake environment hands out a logging function
   proxy - and every guard call was traced as a statement (25k lines of
   `__LC[21]()` in the old obf_4 result, the block truncated and the run
   died). Related: luau-ast lines are **0-based** (like `vmmap`'s `lines[l1]`);
   the old offset math read them 1-based and landed one line early, "fixed"
   by the `find('do')` search - the reworked guards use exact offsets.
4. **Trace throttle** (envlog's `emit`): a block that reaches `max_block`
   no longer errors LOOP (which killed the run at its first hot loop).
   Instead the tracer pushes a **continuation block** (whatever survives the
   loop lands there) and silences itself: emissions are dropped (a counter
   every 65536th drop still runs `checkBudget`, so the budget and heartbeat
   stay enforced). A guarded loop's `__VMBEAT` (every 4096 iterations) keeps
   the silence alive while it churns; its exit (`__LC.r`) or the beats going
   stale (0.5 s without one - a `return` from inside the loop, an unguarded
   chunk) turns tracing back on. With `CFG.vm_pause` (set by the plugin)
   time spent silent does not count against the budget: `--budget` bounds
   traced behaviour, the spin bound bounds the whole run. The hooks
   (`E.__VMHOT`, `E.__VMBEAT`) are hidden from the script's environment walk
   through `DEVIRT_CAPTURE`, like the `__PID` family. A loop's emissions stay
   in the result unless they were actually drowning the tracer - the block
   limit decides, not the loop's shape.
5. Trace run like `generic`, but with `cfg.heartbeat = 0`: pure-compute
   phases are normal here (payload decode), so the 20 s output-stall kill is
   disabled - the guards, not the stall detector, bound the run.
6. `take_p2d` / `p2d_miss` / `take_chunks` (discovered loadstring'd stages
   are kept next to the result as `.chunk_<key>.lua`) / `take_strings`,
   render, and - with `--strings` - the decrypted strings are also copied
   next to the result file.

Timing reference (sandbox): cokeboys full run ~30 s with a 25 s spin bound;
the synthetic hot-loop test finishes 200k emitting iterations in ~1 s.

## Unlocking the full decode (user workflow)

1. The user runs `download/qo_bootstrapper_p2d.lua` (generated with
   `scripts/make_p2d_recorder.py` from a trace of their script - the obf_4
   variant carries the bootstrapper's exact probe: Frame 159x288, 3
   `Path2DControlPoint`s, 12 queries) in a real client (executor/Studio). It
   reproduces the probe bit-exactly and prints a `==P2D== ... ==END==` block.
2. `python3 scripts/parse_p2d_paste.py <paste file> --out <input>.path2d`
   writes the cache next to the input (or the paste is applied with
   `aurora/scripts/apply_p2d2.py` in the Luarmor-chain workflow).
3. Re-run the deob: `load_p2d_cache` replays the real answers, the stage key
   decodes and the VM proceeds past the spin/buffer death - deeper trace +
   strings + the loadstring'd next stage as a chunk file.

## Lifting (future work)

The dispatcher is the classic shape, so `vmmap` machinery applies after
unwrapping the `AstExprGroup` around the fetch; opcodes are polymorphic per
script (fingerprinting needed, CEREBRO_VIRTUAL.md §3.B), operands come from
parallel arrays rather than encoded instruction words, and handlers reference
captured upvalues directly (`U[t[x]] = _playerModelCache`). A lifter would
map handler semantics (the if-chain leaves are readable: `U[p[x]]=U[t[x]]<U[H[x]]`
= LT) to IR per pc-interval - the ironbrew1 `devirt.py` walk pattern. Not
started; the static suite in `v148_suite/` (his "Luraph_Complete_Deobfuscation_
Suite.old.zip") produced only heuristic output (`Function_N` bodies full of
dead math) - the trace route recovers more real behaviour per hour spent.
