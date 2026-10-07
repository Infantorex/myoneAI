@echo off
REM ==============================================================================
REM myoneAI — Test Suite Runner
REM ==============================================================================
SET VENV_PYTEST=%~dp0..\.venv\Scripts\pytest.exe

IF NOT EXIST "%VENV_PYTEST%" (
    echo [ERROR] Pytest not found in .venv.
    exit /b 1
)

"%VENV_PYTEST%" -v %*
