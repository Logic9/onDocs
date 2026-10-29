#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"

# Activate virtualenv if it exists (optional)
if [ -d "${ROOT_DIR}/.venv" ] && [ -f "${ROOT_DIR}/.venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source "${ROOT_DIR}/.venv/bin/activate"
fi

cd "${ROOT_DIR}"

echo "Starting backend on ${BACKEND_HOST}:${BACKEND_PORT}..."
uvicorn backend.main:app --host "${BACKEND_HOST}" --port "${BACKEND_PORT}" &
BACK_PID=$!

echo "Starting frontend on ${FRONTEND_HOST}:${FRONTEND_PORT}..."
npm --prefix "${ROOT_DIR}/frontend" run dev -- --hostname "${FRONTEND_HOST}" --port "${FRONTEND_PORT}" &
FRONT_PID=$!

cleanup() {
  echo "Shutting down..."
  kill "${BACK_PID}" "${FRONT_PID}" 2>/dev/null || true
}

trap cleanup INT TERM EXIT

# Portable wait for either process to exit (POSIX lacks wait -n)
while true; do
  if ! kill -0 "${BACK_PID}" 2>/dev/null; then
    wait "${FRONT_PID}" 2>/dev/null || true
    break
  fi
  if ! kill -0 "${FRONT_PID}" 2>/dev/null; then
    wait "${BACK_PID}" 2>/dev/null || true
    break
  fi
  sleep 1
done
