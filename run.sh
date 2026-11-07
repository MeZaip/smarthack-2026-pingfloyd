#!/usr/bin/env bash
# Start SafeHouse locally: the AI gateway (optional) + the web UI / JSON API.
#
#   ./run.sh                 gateway (if an API key / Ollama is configured) + UI on http://127.0.0.1:8000
#   ./run.sh --demo          same, with a separate demo history pre-loaded from tests/fixtures/synthetic
#   ./run.sh --no-ai         UI only; the assistant uses the built-in, verified texts
#   ./run.sh --port 9000     UI on another port
#   ./run.sh --host 0.0.0.0  UI on another address, e.g. "$(tailscale ip -4)" (no login: keep it private)
#
# Everything runs unprivileged; the AI gateway always listens on 127.0.0.1 only. Live scans are separate:
#   .venv/bin/python -m netcheck scan --confirm      (asks for sudo only for nmap)
# Ctrl+C stops all services started here.
set -euo pipefail
cd "$(dirname "$0")"

PORT=8000
HOST=127.0.0.1
DEMO=0
AI=1
while [[ $# -gt 0 ]]; do
  case "$1" in
    --demo) DEMO=1 ;;
    --no-ai) AI=0 ;;
    --port) PORT="${2:?--port needs a number}"; shift ;;
    --host) HOST="${2:?--host needs an address}"; shift ;;
    -h|--help) sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown option: $1 (see ./run.sh --help)" >&2; exit 2 ;;
  esac
  shift
done

# ---------------------------------------------------------------- python env
PY=.venv/bin/python
if [[ ! -x "$PY" ]]; then
  echo "• Creating .venv ..."
  python3 -m venv .venv
fi
STAMP=.venv/.requirements.sha
WANT=$(sha256sum requirements.txt | cut -d' ' -f1)
if [[ ! -f "$STAMP" || "$(cat "$STAMP")" != "$WANT" ]]; then
  echo "• Installing requirements ..."
  "$PY" -m pip install -q --upgrade pip
  "$PY" -m pip install -q -r requirements.txt
  echo "$WANT" > "$STAMP"
fi

# ---------------------------------------------------------------- settings (.env is optional, never committed)
env_value() {   # value from the environment, else from .env, else empty
  local v="${!1:-}"
  if [[ -z "$v" && -f .env ]]; then
    v=$(grep -E "^$1=" .env | tail -1 | cut -d= -f2- | tr -d "\"'" || true)
  fi
  printf '%s' "$v"
}
GW_PORT=$(env_value NETCHECK_GATEWAY_PORT); GW_PORT=${GW_PORT:-8787}
BACKEND=$(env_value NETCHECK_GATEWAY_BACKEND); BACKEND=${BACKEND:-claude}

if [[ $DEMO -eq 1 ]]; then
  export NETCHECK_DB="$HOME/.netcheck/demo.sqlite"
  echo "• Demo history: $NETCHECK_DB (your real history is not touched)"
  "$PY" -m netcheck history delete --yes >/dev/null 2>&1 || true
  "$PY" -m netcheck history add tests/fixtures/synthetic/ >/dev/null || true
fi

# ---------------------------------------------------------------- services
PIDS=()
cleanup() {
  for pid in "${PIDS[@]:-}"; do [[ -n "$pid" ]] && kill "$pid" 2>/dev/null || true; done
  wait 2>/dev/null || true
  echo; echo "• Stopped."
}
trap cleanup EXIT
trap 'exit 130' INT TERM

if [[ $AI -eq 1 ]]; then
  if [[ "$BACKEND" == "claude" && -z "$(env_value ANTHROPIC_API_KEY)" ]]; then
    echo "• AI gateway: skipped (no ANTHROPIC_API_KEY in the environment or .env)."
    echo "  The assistant will answer from the built-in texts. To enable AI: cp .env.example .env and set the key,"
    echo "  or set NETCHECK_GATEWAY_BACKEND=ollama with a local Ollama model."
    export NETCHECK_LLM_PROVIDER=none
  else
    echo "• AI gateway ($BACKEND) on http://127.0.0.1:$GW_PORT ..."
    "$PY" -m gateway --host 127.0.0.1 --port "$GW_PORT" &
    PIDS+=($!)
    export NETCHECK_AI_URL="http://127.0.0.1:$GW_PORT"
    for _ in $(seq 1 20); do
      curl -fsS "http://127.0.0.1:$GW_PORT/health" >/dev/null 2>&1 && break
      kill -0 "${PIDS[-1]}" 2>/dev/null || { echo "  ✖ gateway exited; continuing with built-in answers"; export NETCHECK_LLM_PROVIDER=none; break; }
      sleep 0.3
    done
  fi
else
  echo "• AI: off (--no-ai); the assistant answers from the built-in texts."
  export NETCHECK_LLM_PROVIDER=none
fi

echo "• Web UI + JSON API on http://$HOST:$PORT   (Ctrl+C to stop)"
"$PY" -m netcheck serve --host "$HOST" --port "$PORT" &
PIDS+=($!)
wait -n "${PIDS[@]}"
