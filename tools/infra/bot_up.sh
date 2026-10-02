#!/usr/bin/env bash
# Levanta el bot CON watchdog (todo daemonizado con doble-fork).
# Úsalo también tras un despertar del sandbox o un rollback.
#
# Requisito: token en /home/z/.secrets/discord_token (copia persistente,
# sobrevive a los restores del sandbox) o ya presente en bot/config.json.
set -euo pipefail
cd /home/z/my-project
mkdir -p /home/z/.secrets bot

# 1) asegurar config.json desde la copia persistente
if [ ! -f bot/config.json ] || ! python3 -c "import json;sys.exit(0 if json.load(open('bot/config.json')).get('token') else 1)" 2>/dev/null; then
  if [ -s /home/z/.secrets/discord_token ]; then
    tok="$(tr -d ' \t\r\n' < /home/z/.secrets/discord_token)"
    python3 - "$tok" <<'PY'
import json, sys
tok = sys.argv[1]
try:
    cfg = json.load(open("bot/config.json"))
except Exception:
    cfg = {}
cfg["token"] = tok
json.dump(cfg, open("bot/config.json", "w"), indent=2, ensure_ascii=False)
PY
    echo "[+] token restaurado en bot/config.json"
  fi
fi

# 2) arrancar el bot (start.sh valida el token y compila luau si hace falta)
bash bot/start.sh --bg

# 3) arrancar/asegurar el watchdog (si ya vive, no duplicar)
if ! pgrep -f "bot_watchdog\.sh" >/dev/null 2>&1; then
  mkdir -p bot
  : > bot/watchdog.log
  DAEMON_LOG=/home/z/my-project/bot/watchdog.log python3 scripts/daemonize.py bash scripts/bot_watchdog.sh
  sleep 1
  pgrep -f "bot_watchdog\.sh" >/dev/null && echo "[+] watchdog corriendo — log: bot/watchdog.log"
else
  echo "[+] watchdog ya estaba corriendo"
fi

echo "[i] parar todo:  pkill -f bot_watchdog.sh; pkill -f bot/bot.mjs"
