#!/usr/bin/env bash
# Start API + frontend for the HANA → BigQuery stub demo in one terminal.
# Ctrl+C stops both. From repo root: ./scripts/run_demo.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

API_PORT="${API_PORT:-8080}"
FE_PORT="${FE_PORT:-3000}"
API_PID=""

cleanup() {
  if [[ -n "${API_PID}" ]] && kill -0 "${API_PID}" 2>/dev/null; then
    kill "${API_PID}" 2>/dev/null || true
    wait "${API_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required (3.12+)." >&2
  exit 1
fi
if ! command -v npm >/dev/null 2>&1; then
  echo "npm is required (Node 20+)." >&2
  exit 1
fi

if [[ ! -d .venv ]]; then
  echo "Creating .venv and installing Python deps (editable + dev)..."
  python3 -m venv .venv
  .venv/bin/pip install -U pip
  .venv/bin/pip install -e ".[dev]"
elif ! .venv/bin/python -c "import uvicorn" 2>/dev/null; then
  echo "Installing Python deps into .venv..."
  .venv/bin/pip install -e ".[dev]"
fi

if [[ ! -d frontend/node_modules ]]; then
  echo "Installing frontend dependencies (npm ci)..."
  (cd frontend && npm ci)
fi

echo "Starting API on port ${API_PORT}..."
.venv/bin/python -m uvicorn presentation.api.main:app --host 0.0.0.0 --port "${API_PORT}" &
API_PID=$!

echo -n "Waiting for API health"
for _ in $(seq 1 60); do
  if ! kill -0 "${API_PID}" 2>/dev/null; then
    echo >&2
    echo "API process exited before becoming healthy." >&2
    exit 1
  fi
  if curl -sf "http://127.0.0.1:${API_PORT}/health" >/dev/null 2>&1; then
    echo " — ok"
    break
  fi
  echo -n "."
  sleep 1
done
if ! curl -sf "http://127.0.0.1:${API_PORT}/health" >/dev/null 2>&1; then
  echo >&2
  echo "Timed out waiting for http://127.0.0.1:${API_PORT}/health" >&2
  exit 1
fi

echo
echo "Open http://localhost:${FE_PORT} — create a programme (customer_id: dev-tenant) → HANA → BigQuery."
echo "API: http://127.0.0.1:${API_PORT}/docs  ·  Curl demo: BASE_URL=http://127.0.0.1:${API_PORT}/api/v1 ./scripts/demo_hana_bigquery.sh"
echo "Press Ctrl+C to stop."
echo

cd frontend
npm run dev
