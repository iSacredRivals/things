#!/usr/bin/env bash
# Sweep RobloxLocaleId values for the hermanos stage-1 VM locale gate
LOCALES="$@"
cd /home/z/my-project
for L in $LOCALES; do
  echo "=== locale: $L"
  timeout 240 python3 scripts/run_dump5_deep.py --no-flat-env --locale "$L" \
    --cfg executor=Delta --cfg ptrace=1 \
    --vmcap 5000000 --budget 40 --timeout 200 \
    --raw /tmp/herm_loc.txt --out /tmp/herm_loc.luau 2>/dev/null | grep -a "run status"
  # how far did it get? (activity after the RobloxLocaleId read)
  NLOC=$(grep -ac "RobloxLocaleId" /tmp/herm_loc.txt 2>/dev/null)
  AFTER=$(grep -an "RobloxLocaleId" /tmp/herm_loc.txt 2>/dev/null | head -1 | cut -d: -f1)
  TOTAL=$(wc -l < /tmp/herm_loc.txt 2>/dev/null)
  STMTS=$(grep -a "statements recorded" /tmp/herm_loc.txt 2>/dev/null)
  echo "    locale reads: $NLOC  total-lines: $TOTAL  $STMTS"
  if [ -n "$AFTER" ]; then
    # show proxy activity after the locale read
    sed -n "${AFTER},$TOTAL p" /tmp/herm_loc.txt | grep -a "\[index\]\|\[call\]\|\[ctor\]" | head -5 | cut -c1-110
  fi
done
