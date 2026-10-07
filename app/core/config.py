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

    # AI Provider Settings (Cloud API - Zero local LLMs)
    ai_provider: str = Field(default="gemini", description="AI provider (gemini, openai, groq, mock)")
    ai_api_key: Optional[str] = Field(default=None, description="AI Cloud API key")
    ai_model: str = Field(default="gemini-1.5-flash", description="AI model name")
    ai_base_url: Optional[str] = Field(default=None, description="Custom base URL for OpenAI-compatible providers")
    ai_timeout: float = Field(default=30.0, description="AI inference request timeout in seconds")
    ai_temperature: float = Field(default=0.7, description="AI sampling temperature")
    ai_max_output_tokens: int = Field(default=500, description="Max generated tokens for concise speech")
    ai_max_history_messages: int = Field(default=12, description="Maximum conversation history turns retained")

    # Speech-to-Text (STT) Settings
    stt_provider: str = Field(default="google", description="STT provider (google, groq, mock)")
    stt_api_key: Optional[str] = Field(default=None, description="STT API key if required")
    stt_model: Optional[str] = Field(default=None, description="STT model name")
    stt_language: str = Field(default="ta-IN", description="STT recognition language code")

    # Audio & Voice Activity Detection (VAD) Settings
    audio_sample_rate: int = Field(default=16000, description="Audio sample rate (Hz)")
    audio_channels: int = Field(default=1, description="Audio channels (1=mono)")
    audio_max_duration: float = Field(default=15.0, description="Maximum recording duration in seconds")
    voice_activity_enabled: bool = Field(default=True, description="Enable automatic VAD silence detection")
    vad_energy_threshold: float = Field(default=500.0, description="VAD RMS energy trigger threshold")
    vad_silence_duration: float = Field(default=1.5, description="Silence duration to end speech (seconds)")

    # Text-to-Speech (TTS) Settings
    tts_provider: str = Field(default="edge-tts", description="TTS provider (edge-tts, mock)")
    tts_api_key: Optional[str] = Field(default=None, description="TTS API key if required")
    tts_model: Optional[str] = Field(default=None, description="TTS model identifier")
    tts_language: str = Field(default="ta-IN", description="Default TTS language code")
    tts_voice: str = Field(default="ta-IN-PallaviNeural", description="Tamil neural voice code")
    tts_speed: float = Field(default=1.0, description="Speech playback speed multiplier (1.0 = normal)")
    tts_volume: float = Field(default=1.0, description="Speech volume multiplier (1.0 = normal)")
    tts_timeout: float = Field(default=30.0, description="TTS synthesis timeout in seconds")

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
