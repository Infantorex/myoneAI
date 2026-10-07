"""Configuration management for myoneAI / Tamil JARVIS.

Loads environment variables with validation and provides safe, resource-friendly access.
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# Project root directory (2 levels up from app/core)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Application configuration schema with environment variable overrides."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # General App Settings
    app_env: str = Field(default="development", description="Application environment")
    jarvis_name: str = Field(default="JARVIS", description="Assistant identity name")
    default_language: str = Field(default="ta-IN", description="Default spoken language code")

    # Logging Settings
    log_level: str = Field(default="INFO", description="Logging verbosity level")
    log_file: str = Field(default="logs/jarvis.log", description="Relative or absolute log path")

    # AI Provider Settings (Cloud API)
    ai_provider: str = Field(default="gemini", description="AI provider (gemini, openai, etc.)")
    ai_api_key: Optional[str] = Field(default=None, description="AI Cloud API key")
    ai_model: str = Field(default="gemini-1.5-flash", description="AI model name")

    # Speech-to-Text (STT) Settings
    stt_provider: str = Field(default="google", description="STT provider")
    stt_api_key: Optional[str] = Field(default=None, description="STT API key if required")
    stt_model: Optional[str] = Field(default=None, description="STT model name")

    # Text-to-Speech (TTS) Settings
    tts_provider: str = Field(default="edge-tts", description="TTS provider")
    tts_api_key: Optional[str] = Field(default=None, description="TTS API key if required")
    tts_voice: str = Field(default="ta-IN-PallaviNeural", description="Tamil voice code")

    # Security & Permissions
    require_confirmation_for_system_actions: bool = Field(
        default=True,
        description="Whether system/destructive actions require explicit user confirmation",
    )

    # Web Dashboard Settings
    web_api_url: str = Field(default="http://localhost:8000", description="Backend/Vercel API URL")

    # Directories
    base_dir: Path = Field(default=PROJECT_ROOT, description="Base directory path")

    @property
    def log_path(self) -> Path:
        """Return the absolute path to the log file."""
        log_p = Path(self.log_file)
        if log_p.is_absolute():
            return log_p
        return self.base_dir / log_p

    @property
    def data_path(self) -> Path:
        """Return the absolute path to data directory."""
        return self.base_dir / "data"

    @property
    def is_ai_configured(self) -> bool:
        """Check if AI API key is configured."""
        return bool(self.ai_api_key and self.ai_api_key.strip() and not self.ai_api_key.startswith("your_"))

    def get_safe_dict(self) -> dict:
        """Return dictionary representation with sensitive credentials masked."""
        data = self.model_dump()
        for key in ["ai_api_key", "stt_api_key", "tts_api_key"]:
            val = data.get(key)
            if val:
                masked = f"{val[:4]}...{val[-4:]}" if len(val) > 8 else "***"
                data[key] = masked
            else:
                data[key] = None
        data["base_dir"] = str(self.base_dir)
        return data


@lru_cache()
def get_settings() -> Settings:
    """Return cached singleton instance of application settings."""
    return Settings()
