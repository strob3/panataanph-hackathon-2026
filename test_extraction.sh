#!/usr/bin/env bash
set -e

# Detect Python virtual environment path (Linux/macOS vs Windows Git Bash)
if [ -f ".venv/Scripts/python.exe" ]; then
    VENV_PY=".venv/Scripts/python.exe"
    VENV_PYTEST=".venv/Scripts/pytest.exe"
elif [ -f ".venv/bin/python" ]; then
    VENV_PY=".venv/bin/python"
    VENV_PYTEST=".venv/bin/pytest"
else
    echo "[!] Virtual environment not found. Setting up .venv..."
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
        VENV_PYTEST=".venv/Scripts/pytest.exe"
    else
        VENV_PY=".venv/bin/python"
        VENV_PYTEST=".venv/bin/pytest"
    fi

    echo "[!] Installing dependencies..."
    "$VENV_PY" -m pip install -r requirements-dev.txt
    echo "[✓] Environment ready."
fi

# 2. Check Ollama status
echo "=== Checking Local AI Runtime (Ollama) ==="
if curl -s http://127.0.0.1:11434/api/tags > /dev/null 2>&1; then
    echo "[✓] Ollama is running on http://127.0.0.1:11434"
    if curl -s http://127.0.0.1:11434/api/tags | grep -q "qwen3:4b"; then
        echo "[✓] Model 'qwen3:4b' found. Live AI extraction will run."
    else
        echo "[!] Model 'qwen3:4b' not detected. Run: ollama pull qwen3:4b"
        echo "    (Pipeline will run with offline fallback mode)"
    fi
else
    echo "[!] Ollama is NOT running."
    echo "    To run live AI model:"
    echo "      1. Install Ollama: https://ollama.ai"
    echo "      2. Start daemon: ollama serve"
    echo "      3. Pull model:   ollama pull qwen3:4b"
    echo "    (Pipeline will run with offline fallback mode)"
fi

echo ""
echo "=== Running Unit & Pipeline Tests ==="
"$VENV_PYTEST" tests/test_extraction.py -v

echo ""
echo "=== Running End-to-End Extraction Workflow ==="
"$VENV_PY" scripts/test_extraction_e2e.py
