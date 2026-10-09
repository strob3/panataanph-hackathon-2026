#!/usr/bin/env bash

# python3 -m venv .venv && ./.venv/bin/pip install -r requirements-dev.txt
set -e

# Kill all background jobs on script exit or interrupt
trap 'kill $(jobs -p) 2>/dev/null' EXIT INT TERM

# Check for backend virtual environment
if [ ! -f ".venv/bin/python" ]; then
  echo "Error: Python venv not found at .venv/bin/python."
  echo "Run: python3 -m venv .venv && ./.venv/bin/pip install -r requirements-dev.txt"
  exit 1
fi

# Check for frontend dependencies
if [ ! -d "frontend/node_modules" ]; then
  echo "Notice: frontend/node_modules missing. Running npm install..."
  (cd frontend && npm install)
fi

echo "Starting backend (http://127.0.0.1:8000) and frontend (http://127.0.0.1:5173)..."
./.venv/bin/python -m uvicorn backend.main:app --app-dir src --reload --host 127.0.0.1 --port 8000 &
(cd frontend && npm run dev) &

wait
