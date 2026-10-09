@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo  PanataanPH - AI Extraction Pipeline Test (Windows)
echo ========================================================

REM 1. Check Python virtual environment
if not exist ".venv\Scripts\python.exe" (
    echo [!] Virtual environment not found. Setting up .venv...
    where python >nul 2>&1 && python -m venv .venv
    if not exist ".venv\Scripts\python.exe" (
        echo [ERROR] Python not found. Please install Python 3.10+.
        pause
        exit /b 1
    )
    echo [!] Installing dependencies...
    .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
)

REM 2. Check Ollama
echo.
echo === Checking Local AI Runtime (Ollama) ===
curl -s http://127.0.0.1:11434/api/tags >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Ollama is running on http://127.0.0.1:11434
    curl -s http://127.0.0.1:11434/api/tags | findstr /i "qwen3:4b" >nul 2>&1
    if %errorlevel% equ 0 (
        echo [OK] Model 'qwen3:4b' detected. Live AI extraction will run.
    ) else (
        echo [!] Model 'qwen3:4b' not detected. Run: ollama pull qwen3:4b
        echo     (Pipeline will run with offline fallback mode)
    )
) else (
    echo [!] Ollama is NOT running.
    echo     To run live AI model:
    echo       1. Install Ollama: https://ollama.ai
    echo       2. Start daemon:   ollama serve
    echo       3. Pull model:     ollama pull qwen3:4b
    echo     (Pipeline will run with offline fallback mode)
)

echo.
echo === Running Unit & Pipeline Tests ===
.\.venv\Scripts\pytest.exe tests\test_extraction.py -v

echo.
echo === Running End-to-End Extraction Workflow ===
.\.venv\Scripts\python.exe scripts\test_extraction_e2e.py

echo.
echo ========================================================
echo  Tests finished!
echo ========================================================
pause
