@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo  PanataanPH - Windows Startup Script
echo ========================================================

REM 1. Locate Python executable for virtualenv creation
set "PY_CMD="
where python >nul 2>&1 && set "PY_CMD=python"
if "%PY_CMD%"=="" where py >nul 2>&1 && set "PY_CMD=py"

if "%PY_CMD%"=="" (
    echo [ERROR] Python not found in PATH.
    echo Please install Python 3.10+ from https://www.python.org/ and check "Add Python to PATH".
    pause
    exit /b 1
)

REM 2. Check / Setup Python Virtual Environment
if not exist ".venv\Scripts\python.exe" (
    echo [!] Virtual environment not found. Creating .venv...
    %PY_CMD% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [!] Installing backend dependencies...
    .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install backend dependencies.
        pause
        exit /b 1
    )
    echo [OK] Backend environment ready.
)

REM 3. Check / Setup Frontend Dependencies
if not exist "frontend\node_modules" (
    echo [!] Frontend dependencies not found. Installing via npm...
    where npm.cmd >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Node.js / npm not found in PATH.
        echo Please install Node.js 20+ from https://nodejs.org/
        pause
        exit /b 1
    )
    cd frontend
    call npm.cmd install
    cd ..
    echo [OK] Frontend dependencies ready.
)

echo.
echo Starting PanataanPH services in separate windows...
echo  - Backend API: http://127.0.0.1:8000/docs
echo  - Frontend:    http://127.0.0.1:5173
echo.

REM 4. Launch backend and frontend in separate background command windows
start "PanataanPH - Backend (FastAPI)" cmd /k ".\.venv\Scripts\python.exe -m uvicorn backend.main:app --app-dir src --reload --host 127.0.0.1 --port 8000"
start "PanataanPH - Frontend (Vite)" cmd /k "cd frontend && npm.cmd run dev"

echo Services started! Close the respective popup windows to stop them.
echo Opening browser at http://127.0.0.1:5173...
timeout /t 3 /nobreak >nul
start http://127.0.0.1:5173
