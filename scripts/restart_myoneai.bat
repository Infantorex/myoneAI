@echo off
setlocal enabledelayedexpansion

echo ======================================================================
echo   myoneAI — Tamil JARVIS Restart Utility
echo ======================================================================
echo.

cd /d "%~dp0"

echo [*] Stopping running assistant instance...
call stop_myoneai.bat

echo [*] Waiting 2 seconds for resource cleanup...
timeout /t 2 /nobreak >nul

echo [*] Starting fresh assistant instance...
start "myoneAI Assistant" call start_myoneai.bat
