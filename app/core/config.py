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
    app_name: str = Field(default="myoneAI", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    app_env: str = Field(default="development", description="Application environment")
    jarvis_name: str = Field(default="JARVIS", description="Assistant identity name")
    language: str = Field(default="ta-IN", description="Default spoken language code")
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

    # Voice Pipeline & Conversation Loop Settings (Phase 5)
    voice_language: str = Field(default="ta-IN", description="Primary spoken language code for conversation loop")
    voice_listen_timeout: float = Field(default=15.0, description="Listening timeout for utterance in seconds")
    voice_interactive_mode: bool = Field(default=False, description="Whether conversation runs continuously in interactive mode")
    stt_timeout: float = Field(default=30.0, description="STT transcription timeout in seconds")

    # Wake Word Settings (Phase 6)
    wake_word_enabled: bool = Field(default=True, description="Enable background wake word listener")
    wake_word: str = Field(default="jarvis", description="Configurable wake phrase")
    wake_word_language: str = Field(default="en-US", description="Wake word recognition language")
    wake_word_sensitivity: float = Field(default=0.5, description="Wake word sensitivity threshold (0.0 - 1.0)")
    wake_word_timeout: float = Field(default=1.0, description="Wake word detection chunk timeout in seconds")
    wake_word_cooldown: float = Field(default=1.5, description="Debounce cooldown between wake detections in seconds")
    wake_response_enabled: bool = Field(default=True, description="Speak a short acknowledgment upon wake word detection")
    wake_response_text: str = Field(default="சொல்லுங்க.", description="Acknowledgment response text (Tamil or English)")
    wake_word_on_battery: bool = Field(default=True, description="Whether wake word runs when on battery power")
    wake_word_provider: str = Field(default="local", description="Wake word engine (local, mock, energy)")
    wake_word_api_key: Optional[str] = Field(default=None, description="Wake word provider API key if applicable")

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

    # PC Assistant Tools Settings (Phase 8)
    tools_enabled: bool = Field(default=True, description="Enable local PC assistant tools")
    tool_default_timeout: float = Field(default=10.0, description="Default tool execution timeout in seconds")
    tool_confirmation_timeout: float = Field(default=30.0, description="Pending confirmation expiry timeout in seconds")
    allowed_directories: str = Field(default="", description="Comma-separated allowed directories for filesystem tools")
    allowed_applications: str = Field(default="", description="Comma-separated custom allowed application mappings")
    screenshot_directory: str = Field(default="data/screenshots", description="Directory path to save screenshots")
    screenshot_retention_days: int = Field(default=7, description="Number of days to retain screenshots before cleanup")

    # Lightweight System Monitoring & Alerts (Phase 9)
    monitoring_enabled: bool = Field(default=True, description="Enable lightweight system monitoring & alerts")
    monitoring_interval_seconds: int = Field(default=60, description="Background monitoring check interval in seconds")
    cpu_warning_threshold: float = Field(default=85.0, description="CPU usage percent warning threshold")
    cpu_critical_threshold: float = Field(default=95.0, description="CPU usage percent critical threshold")
    memory_warning_threshold: float = Field(default=80.0, description="Memory usage percent warning threshold")
    memory_critical_threshold: float = Field(default=90.0, description="Memory usage percent critical threshold")
    disk_warning_threshold: float = Field(default=85.0, description="Disk usage percent warning threshold")
    disk_critical_threshold: float = Field(default=95.0, description="Disk usage percent critical threshold")
    battery_low_threshold: float = Field(default=20.0, description="Battery percent low/warning threshold")
    battery_critical_threshold: float = Field(default=10.0, description="Battery percent critical threshold")
    alert_cooldown_seconds: int = Field(default=300, description="Cooldown period in seconds to suppress duplicate alerts")

    # AI Memory Settings (Phase 7)
    memory_enabled: bool = Field(default=True, description="Enable long-term controlled AI memory")
    memory_max_results: int = Field(default=5, description="Maximum relevant memory items retrieved for AI prompt context")
    memory_max_context_chars: int = Field(default=3000, description="Maximum total character length for memory prompt context")
    memory_require_confirmation: bool = Field(default=True, description="Require confirmation before clear/destructive memory actions")
    memory_database_path: str = Field(default="data/memory.db", description="SQLite database path for structured memories")

    # Productivity & Task System Settings (Phase 10)
    productivity_enabled: bool = Field(default=True, description="Enable local productivity and task management system")
    productivity_database_path: str = Field(default="data/productivity.db", description="SQLite database path for tasks, reminders, and notes")
    productivity_check_interval: int = Field(default=30, description="Scheduler check interval in seconds for due reminders")
    max_active_timers: int = Field(default=5, description="Maximum simultaneous active timers allowed")
    max_missed_reminders_on_startup: int = Field(default=5, description="Maximum past due reminders to trigger on startup recovery")
    productivity_timezone: str = Field(default="", description="Optional timezone override (e.g. Asia/Kolkata); defaults to system local timezone")

    # Web Dashboard Settings (Phase 11)
    web_enabled: bool = Field(default=True, description="Enable local web dashboard and API")
    web_host: str = Field(default="127.0.0.1", description="Local web server host IP (localhost only)")
    web_port: int = Field(default=8000, description="Local web server port")
    web_auth_enabled: bool = Field(default=True, description="Enable token authentication for web API")
    web_auth_token: str = Field(default="", description="Secret bearer token for authenticating web dashboard")
    web_status_refresh_seconds: int = Field(default=10, description="Client status refresh interval in seconds")
    web_chat_max_length: int = Field(default=2000, description="Maximum characters allowed in web chat messages")
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
    def memory_db_path(self) -> Path:
        """Return the absolute path to SQLite memory database."""
        db_p = Path(self.memory_database_path)
        if db_p.is_absolute():
            return db_p
        return self.base_dir / db_p

    @property
    def screenshot_dir_path(self) -> Path:
        """Return the absolute path to screenshot directory."""
        s_p = Path(self.screenshot_directory)
        if s_p.is_absolute():
            return s_p
        return self.base_dir / s_p

    @property
    def is_ai_configured(self) -> bool:
        """Check if AI API key is configured."""
        return bool(self.ai_api_key and self.ai_api_key.strip() and not self.ai_api_key.startswith("your_"))

    def get_safe_dict(self) -> dict:
        """Return dictionary representation with sensitive credentials masked."""
        data = self.model_dump()
        for key in ["ai_api_key", "stt_api_key", "tts_api_key", "wake_word_api_key", "web_auth_token"]:
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
