#!/usr/bin/env bash
set -euo pipefail

# === Config (adjust if you like) ===
APP1_PATH="./src/App/streamlit_drools_app.py"
APP2_PATH="./src/App/search.py"

# Default ports (override with env vars if needed)
APP1_PORT="${APP1_PORT:-8501}"
APP2_PORT="${APP2_PORT:-8502}"

VENV_ACTIVATE="venv/bin/activate"
RUN_DIR=".run"
LOG_DIR="logs"
APP1_PID_FILE="${RUN_DIR}/app1.pid"
APP2_PID_FILE="${RUN_DIR}/app2.pid"
APP1_LOG="${LOG_DIR}/app1.log"
APP2_LOG="${LOG_DIR}/app2.log"

# === Helpers ===
need() { command -v "$1" >/dev/null 2>&1 || { echo "Missing dependency: $1"; exit 1; }; }

is_running_pidfile() {
  local pidfile="$1"
  [[ -f "$pidfile" ]] || return 1
  local pid
  pid="$(cat "$pidfile" 2>/dev/null || true)"
  [[ -n "${pid:-}" ]] || return 1
  if ps -p "$pid" >/dev/null 2>&1; then
    return 0
  else
    return 1
  fi
}

ensure_dirs() {
  mkdir -p "$RUN_DIR" "$LOG_DIR"
}

start_one() {
  local app_path="$1"
  local port="$2"
  local pidfile="$3"
  local logfile="$4"

  if is_running_pidfile "$pidfile"; then
    echo "Already running: $app_path (PID $(cat "$pidfile"))"
    return 0
  fi

  # Run Streamlit app in background with logs
  # --server.headless is default in containers, add explicitly
  nohup streamlit run "$app_path" \
    --server.port "$port" \
    --server.headless true \
    --browser.gatherUsageStats false \
    >"$logfile" 2>&1 &

  echo $! > "$pidfile"
  echo "Started $app_path on port $port (PID $(cat "$pidfile")). Logs: $logfile"
}

stop_one() {
  local desc="$1"
  local pidfile="$2"

  if is_running_pidfile "$pidfile"; then
    local pid
    pid="$(cat "$pidfile")"
    echo "Stopping $desc (PID $pid)..."
    kill "$pid" 2>/dev/null || true
    # Give it a moment, then force if needed
    sleep 1
    if ps -p "$pid" >/dev/null 2>&1; then
      kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$pidfile"
    echo "Stopped $desc."
  else
    echo "$desc is not running."
    rm -f "$pidfile" 2>/dev/null || true
  fi
}

status_one() {
  local desc="$1"
  local pidfile="$2"
  if is_running_pidfile "$pidfile"; then
    echo "$desc: RUNNING (PID $(cat "$pidfile"))"
  else
    echo "$desc: NOT RUNNING"
  fi
}

# === Commands ===
cmd_update() {
  need git
  echo "Updating code with git pull..."
  git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "Not a git repo here."; exit 1; }
  git pull --ff-only
  echo "Code updated."
}

cmd_start() {
  ensure_dirs

  # Activate venv
  if [[ ! -f "$VENV_ACTIVATE" ]]; then
    echo "Cannot find $VENV_ACTIVATE. Make sure your venv exists."
    exit 1
  fi
  # shellcheck disable=SC1090
  source "$VENV_ACTIVATE"

  # Ensure streamlit is available
  need streamlit

  start_one "$APP1_PATH" "$APP1_PORT" "$APP1_PID_FILE" "$APP1_LOG"
  start_one "$APP2_PATH" "$APP2_PORT" "$APP2_PID_FILE" "$APP2_LOG"
}

cmd_stop() {
  stop_one "App1 ($APP1_PATH)" "$APP1_PID_FILE"
  stop_one "App2 ($APP2_PATH)" "$APP2_PID_FILE"
}

cmd_status() {
  status_one "App1 ($APP1_PATH)" "$APP1_PID_FILE"
  status_one "App2 ($APP2_PATH)" "$APP2_PID_FILE"
}

cmd_logs() {
  echo "Tail logs (Ctrl+C to stop):"
  echo "  $APP1_LOG"
  echo "  $APP2_LOG"
  echo
  tail -n 100 -F "$APP1_LOG" "$APP2_LOG"
}

usage() {
  cat <<EOF
Usage: $0 <update|start|stop|status|logs>

Commands:
  update   Pull latest code from git (git pull --ff-only)
  start    Activate venv and start both Streamlit apps in background
  stop     Stop both Streamlit apps
  status   Show running status (PIDs)
  logs     Tail both log files

Env vars you can set:
  APP1_PORT (default: $APP1_PORT)
  APP2_PORT (default: $APP2_PORT)
EOF
}

# === Entrypoint ===
ACTION="${1:-}"
case "$ACTION" in
  update) cmd_update ;;
  start)  cmd_start ;;
  stop)   cmd_stop ;;
  status) cmd_status ;;
  logs)   cmd_logs ;;
  *) usage; exit 1 ;;
esac
