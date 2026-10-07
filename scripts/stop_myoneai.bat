@echo off
setlocal enabledelayedexpansion

echo ======================================================================
echo   myoneAI — Tamil JARVIS Shutdown Utility
echo ======================================================================
echo.

cd /d "%~dp0\.."

set "LOCK_FILE=data\myoneai.lock"

if exist "%LOCK_FILE%" (
    set /p JARVIS_PID=<"%LOCK_FILE%"
    if defined JARVIS_PID (
        echo [*] Found active myoneAI process (PID: !JARVIS_PID!). Stopping...
        taskkill /PID !JARVIS_PID! /T /F >nul 2>nul
        if %errorlevel% equ 0 (
            echo [SUCCESS] myoneAI process !JARVIS_PID! terminated cleanly.
        ) else (
            echo [NOTICE] Process was not active or already closed.
        )
    )
    del /f /q "%LOCK_FILE%" >nul 2>nul
) else (
    echo [*] No lock file found. Searching for running JARVIS processes...
    wmic process where "commandline like '%%app.voice.jarvis%%'" call terminate >nul 2>nul
    echo [SUCCESS] Completed stop sequence.
)

echo.
echo [DONE] myoneAI is stopped.
