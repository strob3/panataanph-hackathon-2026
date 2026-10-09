#!/usr/bin/env bash
set -e

# Detect Python virtual environment path (Linux/macOS vs Windows Git Bash)
if [ -f ".venv/Scripts/python.exe" ]; then
    VENV_PY=".venv/Scripts/python.exe"
elif [ -f ".venv/bin/python" ]; then
    VENV_PY=".venv/bin/python"
else
    echo "[!] Virtualenv not found. Creating .venv..."
    if command -v python3 >/dev/null 2>&1; then
        python3 -m venv .venv
    elif command -v python >/dev/null 2>&1; then
        python -m venv .venv
    elif command -v py >/dev/null 2>&1; then
        py -m venv .venv
    else
        echo "Error: Python 3.10+ not found in PATH."
        exit 1
    fi

    if [ -f ".venv/Scripts/python.exe" ]; then
        VENV_PY=".venv/Scripts/python.exe"
    else
        VENV_PY=".venv/bin/python"
    fi

    echo "[!] Installing backend dependencies..."
    "$VENV_PY" -m pip install -r requirements-dev.txt
fi

# Detect npm
if command -v npm.cmd >/dev/null 2>&1; then
    NPM="npm.cmd"
else
    NPM="npm"
fi

# Check frontend dependencies
if [ ! -d "frontend/node_modules" ]; then
    echo "[!] frontend/node_modules missing. Running npm install..."
    (cd frontend && $NPM install)
fi

# Trap to kill background jobs on interrupt
trap 'kill $(jobs -p) 2>/dev/null' EXIT INT TERM

echo "Starting backend (http://127.0.0.1:8000) and frontend (http://127.0.0.1:5173)..."
"$VENV_PY" -m uvicorn backend.main:app --app-dir src --reload --host 127.0.0.1 --port 8000 &
(cd frontend && $NPM run dev) &

wait
