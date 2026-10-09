#!/usr/bin/env bash
set -e

# Use isolated temporary paths for testing so tracked db is untouched
export PANATAANPH_DB_PATH="/tmp/panataanph_test.db"
export PANATAANPH_STORAGE_PATH="/tmp/panataanph_test_storage"
rm -f "$PANATAANPH_DB_PATH"
rm -rf "$PANATAANPH_STORAGE_PATH"

# 1. Bootstrap virtualenv if missing on fresh clone
if [ ! -f ".venv/bin/python" ]; then
    echo "[!] Virtual environment not found. Setting up .venv..."
    python3 -m venv .venv
    echo "[!] Installing dependencies..."
    ./.venv/bin/pip install -r requirements-dev.txt
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
./.venv/bin/pytest tests/test_extraction.py -v

echo ""
echo "=== Running End-to-End Extraction Workflow ==="
./.venv/bin/python scripts/test_extraction_e2e.py
