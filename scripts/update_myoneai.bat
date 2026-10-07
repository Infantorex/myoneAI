@echo off
setlocal enabledelayedexpansion

title myoneAI Update Utility (v1.0.0)

echo ======================================================================
echo   myoneAI — Tamil JARVIS Safe Update Utility
echo ======================================================================
echo.

cd /d "%~dp0\.."

if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

REM 1. Backup user data before update
echo [*] Step 1: Creating safety backup of user databases...
"%PYTHON_EXE%" scripts\backup_data.py
if %errorlevel% neq 0 (
    echo [ERROR] Backup failed. Aborting update for safety.
    pause
    exit /b 1
)

REM 2. Pull latest code from GitHub
echo.
echo [*] Step 2: Fetching updates from GitHub repository...
git pull origin main
if %errorlevel% neq 0 (
    echo [ERROR] Git pull failed. Please check network and resolve conflicts.
    pause
    exit /b 1
)

REM 3. Update Dependencies
echo.
echo [*] Step 3: Checking dependencies...
"%PYTHON_EXE%" -m pip install -r requirements.txt --quiet

REM 4. Run Pre-flight Health Check & Tests
echo.
echo [*] Step 4: Running health diagnostics and verification tests...
"%PYTHON_EXE%" -m app.core.health
"%PYTHON_EXE%" -m pytest -q

if %errorlevel% equ 0 (
    echo.
    echo ======================================================================
    echo   [SUCCESS] myoneAI updated and verified successfully!
    echo ======================================================================
) else (
    echo.
    echo [WARNING] Update installed, but some tests reported issues.
    echo You can restore your data using: python scripts\restore_data.py --backup-file ...
)

pause
