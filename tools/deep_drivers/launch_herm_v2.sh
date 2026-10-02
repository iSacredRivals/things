#!/bin/bash
# Launch the hermanos fast-v2 harness in the background, log exit code + timing.
OUT=/tmp/herm_v2_out.txt
LOG=/tmp/herm_v2_run.log
rm -f "$OUT" "$LOG"
cd deobf
setsid nohup bash -c "
  start=\$(date +%s)
  timeout 3600 ./bin/luau samples/output/herm_fast2_trace.luau.harness.luau > $OUT 2>&1 < /dev/null
  rc=\$?
  end=\$(date +%s)
  echo \"EXIT=\$rc DURATION=\$((end-start))s SIZE=\$(wc -c < $OUT)\" >> $LOG
" > /dev/null 2>&1 &
echo "launched"
