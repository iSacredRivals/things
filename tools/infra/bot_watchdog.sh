#!/usr/bin/env bash
# Watchdog del bot DevAurora Code.
#
# Mantiene el bot vivo MIENTRAS EL SANDBOX ESTÉ DESPIERTO:
#   · si el proceso node muere (crash, logout) → lo relanza en <20 s
#   · si un rollback del sandbox borró bot/config.json → lo restaura desde
#     la copia persistente /home/z/.secrets/discord_token
#
# ⚠️ Cuando el sandbox duerme TODO muere (watchdog incluido). Al despertar,
# relanza el watchdog con:  bash scripts/bot_up.sh
#
# Parar todo: pkill -f bot_watchdog.sh ; pkill -f bot/bot.mjs
set -u
cd /home/z/my-project
SECRETS=/home/z/.secrets/discord_token
CFG=bot/config.json

log() { echo "$(date +%H:%M:%S) [wd] $*" >> bot/watchdog.log; }

restore_token() {
  if [ ! -f "$CFG" ] && [ -s "$SECRETS" ]; then
    local tok; tok="$(tr -d ' \t\r\n' < "$SECRETS")"
    if [ -n "$tok" ]; then
      python3 - "$tok" "$CFG" <<'PY'
import json, sys
tok, path = sys.argv[1], sys.argv[2]
cfg = {}
try:
    cfg = json.load(open(path))
except Exception:
    cfg = {}
cfg["token"] = tok
json.dump(cfg, open(path, "w"), indent=2, ensure_ascii=False)
PY
      log "config.json restaurado desde la copia persistente"
    fi
  fi
}

log "watchdog arriba (PID $$)"
while true; do
  if ! pgrep -f "bot/bot\.mjs" >/dev/null 2>&1; then
    restore_token
    if [ -f "$CFG" ] && python3 -c "import json,sys; sys.exit(0 if json.load(open('bot/config.json')).get('token') else 1)" 2>/dev/null; then
      log "bot caído → relanzando"
      bash bot/start.sh --bg >/dev/null 2>&1 || log "start.sh falló"
    fi
  fi
  sleep 20
done
