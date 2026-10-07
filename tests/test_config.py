"""Unit tests for configuration management (app/core/config.py).
"""

from pathlib import Path
from app.core.config import Settings, get_settings


def test_default_settings():
    """Verify default configuration values."""
    settings = Settings()
    assert settings.jarvis_name == "JARVIS"
    assert settings.default_language == "ta-IN"
    assert settings.app_env in ["development", "production", "testing"]
    assert settings.ai_provider == "gemini"
    assert settings.ai_model == "gemini-1.5-flash"
    assert settings.tts_provider == "edge-tts"
    assert settings.tts_voice == "ta-IN-PallaviNeural"
    assert settings.require_confirmation_for_system_actions is True


def test_path_properties():
    """Verify path helper calculations."""
    settings = Settings()
    assert isinstance(settings.log_path, Path)
    assert isinstance(settings.data_path, Path)
    assert settings.data_path.name == "data"
    assert "jarvis.log" in str(settings.log_path)


def test_safe_dict_masking():
    """Verify that sensitive credentials are masked in get_safe_dict."""
    settings = Settings(ai_api_key="AIzaSyA123456789SecretKey99")
    safe = settings.get_safe_dict()
    assert "SecretKey" not in safe["ai_api_key"]
    assert safe["ai_api_key"].startswith("AIza...")


def test_is_ai_configured():
    """Verify AI configuration check logic."""
    unconfigured = Settings(ai_api_key=None)
    assert unconfigured.is_ai_configured is False

    placeholder = Settings(ai_api_key="your_gemini_api_key_here")
    assert placeholder.is_ai_configured is False

    valid = Settings(ai_api_key="AIzaSyValidKey123")
    assert valid.is_ai_configured is True


def test_singleton_get_settings():
    """Verify that get_settings() returns a consistent instance."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
