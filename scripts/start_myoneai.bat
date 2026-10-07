@echo off
setlocal enabledelayedexpansion

title myoneAI — Tamil JARVIS (v1.0.0)

echo ======================================================================
echo   myoneAI — Tamil JARVIS Production Launcher (v1.0.0)
echo ======================================================================
echo.

cd /d "%~dp0\.."

REM 1. Verify Virtual Environment
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
    where python >nul 2>nul
    if %errorlevel% neq 0 (
        echo [ERROR] Python was not found in .venv or system PATH.
        echo Please install Python 3.10+ and run: python -m venv .venv
        pause
        exit /b 1
    )
    set "PYTHON_EXE=python"
)

REM 2. Run Pre-flight Health Check
echo [*] Running pre-flight system diagnostics...
"%PYTHON_EXE%" -m app.core.health
if %errorlevel% neq 0 (
    echo.
    echo [WARNING] Some health checks failed. Proceeding with caution...
)

REM 3. Launch JARVIS Assistant
echo.
echo [*] Starting myoneAI Voice Assistant & Background Services...
echo [*] Say "JARVIS" or "ஜார்விஸ்" to interact.
echo [*] Press Ctrl+C to stop.
echo.

"%PYTHON_EXE%" -m app.voice.jarvis

if %errorlevel% neq 0 (
    echo.
    echo [NOTICE] Assistant stopped or exited.
)

pause
