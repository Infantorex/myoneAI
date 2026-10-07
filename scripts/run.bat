@echo off
REM ==============================================================================
REM myoneAI — Tamil JARVIS Launcher
REM ==============================================================================
SET VENV_PYTHON=%~dp0..\.venv\Scripts\python.exe

IF NOT EXIST "%VENV_PYTHON%" (
    echo [ERROR] Virtual environment not found at .venv. Please create it first.
    exit /b 1
)

"%VENV_PYTHON%" -m app.core.main %*
