# Configuration Guide — myoneAI (v1.0.0)

All user settings in **myoneAI** are managed via the `.env` file and validated at startup using Pydantic.

---

## 1. Core Settings

| Variable | Default | Description |
| :--- | :--- | :--- |
| `APP_ENV` | `production` | Environment mode (`production`, `development`, `testing`) |
| `JARVIS_NAME` | `JARVIS` | Assistant persona name |
| `DEFAULT_LANGUAGE` | `ta-IN` | Default language code (`ta-IN` for Tamil) |
| `LOG_LEVEL` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `LOG_FILE` | `logs/jarvis.log` | Rotating log file location (max 5 MB x 3 backups) |

---

## 2. AI Provider Settings (Cloud API)

`myoneAI` uses ultra-lightweight cloud API calls with zero heavy local model weights.

| Variable | Default | Description |
| :--- | :--- | :--- |
| `AI_PROVIDER` | `gemini` | Provider choice: `gemini`, `openai`, `groq`, or `mock` |
| `AI_API_KEY` | `""` | Cloud AI API Key |
| `AI_MODEL` | `gemini-1.5-flash` | LLM model identifier |
| `AI_TEMPERATURE` | `0.7` | Sampling temperature for concise natural speech |
| `AI_MAX_OUTPUT_TOKENS` | `500` | Max tokens per turn |
| `AI_MAX_HISTORY_MESSAGES` | `12` | Bounded short-term FIFO context history |

---

## 3. Speech Recognition (STT)

| Variable | Default | Description |
| :--- | :--- | :--- |
| `STT_PROVIDER` | `google` | STT engine (`google`, `groq`, `mock`) |
| `STT_LANGUAGE` | `ta-IN` | Recognition language code |
| `VAD_ENERGY_THRESHOLD` | `500.0` | RMS energy threshold for speech activation |
| `VAD_SILENCE_DURATION` | `1.5` | Silence duration (seconds) to conclude an utterance |

---

## 4. Text-to-Speech (TTS)

| Variable | Default | Description |
| :--- | :--- | :--- |
| `TTS_PROVIDER` | `edge-tts` | High-definition neural speech engine |
| `TTS_VOICE` | `ta-IN-PallaviNeural` | Tamil voice (`ta-IN-PallaviNeural`, `ta-IN-ValluvarNeural`) |
| `TTS_SPEED` | `1.0` | Speech playback rate multiplier |

---

## 5. Security & Permission Layers

| Variable | Default | Description |
| :--- | :--- | :--- |
| `TOOLS_ENABLED` | `true` | Enable controlled PC assistant tools |
| `REQUIRE_CONFIRMATION_FOR_SYSTEM_ACTIONS` | `true` | Mandatory user confirmation before destructive actions |
| `MEMORY_REQUIRE_CONFIRMATION` | `true` | Confirmation token required before clearing memory store |
| `SCREENSHOT_RETENTION_DAYS` | `7` | Retention window for locally captured screenshots |

---

## 6. Local Dashboard & Vercel Cloud Bridge

| Variable | Default | Description |
| :--- | :--- | :--- |
| `WEB_ENABLED` | `true` | Enable local FastAPI dashboard |
| `WEB_HOST` | `127.0.0.1` | Localhost only (zero public exposure) |
| `WEB_PORT` | `8000` | Local dashboard port |
| `WEB_AUTH_ENABLED` | `true` | Require Bearer token for web API |
| `WEB_AUTH_TOKEN` | `""` | Secret token for browser dashboard access |
| `CLOUD_ENABLED` | `false` | Enable outbound laptop ↔ Vercel cloud bridge |
| `CLOUD_TLS_REQUIRED` | `true` | Enforce TLS (HTTPS/WSS) for cloud packets |
