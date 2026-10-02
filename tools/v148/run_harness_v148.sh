#!/bin/bash
# Run the v14.8 harness directly with RSS monitoring
H="$1"; TMO="${2:-540}"
OUT=/tmp/v148_full_out.txt; ERR=/tmp/v148_full_err.txt; RSSLOG=/tmp/v148_rss.log
rm -f "$OUT" "$ERR" "$RSSLOG"
LUAU=deobf/bin/luau
"$LUAU" "$H" > "$OUT" 2> "$ERR" &
LPID=$!
START=$(date +%s)
while kill -0 $LPID 2>/dev/null; do
  NOW=$(date +%s); EL=$((NOW-START))
  if [ $EL -gt $TMO ]; then echo "TIMEOUT after ${EL}s" > /tmp/v148_rc.txt; kill -9 $LPID 2>/dev/null; break; fi
  RSS=$(ps -o rss= -p $LPID 2>/dev/null | tr -d ' ')
  echo "$EL s: RSS=${RSS:-?} KB out=$(wc -c < "$OUT" 2>/dev/null)" >> "$RSSLOG"
  sleep 5
done
wait $LPID 2>/dev/null; RC=$?
[ -f /tmp/v148_rc.txt ] || echo "RC=$RC after $(( $(date +%s) - START ))s" > /tmp/v148_rc.txt
