"""Unit tests for main CLI commands and diagnostic execution (app/core/main.py).
"""

from app.core.main import check_environment, print_diagnostic_status


def test_check_environment():
    """Verify check_environment runs and creates directories if needed."""
    result = check_environment()
    assert result is True


def test_print_diagnostic_status(capsys):
    """Verify diagnostic status output prints expected sections."""
    print_diagnostic_status()
    captured = capsys.readouterr()
    assert "myoneAI — Tamil JARVIS" in captured.out
    assert "Hardware Telemetry" in captured.out
    assert "Service Registry" in captured.out
    assert "Process Memory" in captured.out
