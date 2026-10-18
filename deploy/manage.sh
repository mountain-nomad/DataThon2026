#!/usr/bin/env bash
set -euo pipefail
APP_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export PATH="$APP_DIR/local/node-runtime/node_modules/node/bin:$PATH"
export NEXT_TELEMETRY_DISABLED=1
mkdir -p "$APP_DIR/local/logs"
start_session() {
  local name="$1" directory="$2" command="$3"
  if ! tmux has-session -t "$name" 2>/dev/null; then
    tmux new-session -d -s "$name" -c "$directory" "$command"
  fi
}
case "${1:-status}" in
  build)
    cd "$APP_DIR/frontend"
    node node_modules/next/dist/bin/next build
    cp -a .next/static .next/standalone/.next/
    cp -a public .next/standalone/
    ;;
  start)
    start_session datathon-backend "$APP_DIR/backend" "exec '$APP_DIR/.venv-web/bin/python' -m uvicorn app.main:app --host 127.0.0.1 --port 8000 > '$APP_DIR/local/logs/backend.log' 2>&1"
    start_session datathon-frontend "$APP_DIR/frontend" "exec env HOSTNAME=127.0.0.1 PORT=3000 '$APP_DIR/local/node-runtime/node_modules/node/bin/node' --env-file=.env.local .next/standalone/server.js > '$APP_DIR/local/logs/frontend.log' 2>&1"
    ;;
  tunnel)
    "$APP_DIR/.venv-web/bin/python" "$APP_DIR/deploy/test_site_login.py" -q
    "$APP_DIR/local/bin/ngrok" config check --config "$APP_DIR/local/ngrok.yml"
    start_session datathon-ngrok "$APP_DIR" "exec '$APP_DIR/local/bin/ngrok' http http://127.0.0.1:3000 --config '$APP_DIR/local/ngrok.yml' --inspect=false --log stdout > '$APP_DIR/local/logs/ngrok.log' 2>&1"
    ;;
  stop)
    for name in datathon-ngrok datathon-frontend datathon-backend; do
      tmux kill-session -t "$name" 2>/dev/null || true
    done
    ;;
  status)
    tmux list-sessions -F '#{session_name}' | rg '^datathon-' || true
    curl -fsS http://127.0.0.1:8000/health || true
    curl -fsS http://127.0.0.1:4040/api/tunnels || true
    ;;
  *) echo 'Usage: deploy/manage.sh {build|start|tunnel|status|stop}'; exit 2 ;;
esac
