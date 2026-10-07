# Installation Guide — myoneAI (v1.0.0)

This guide walks you through setting up **myoneAI — Tamil JARVIS** on a Windows PC (Windows 10/11 x64, Intel Core i3 10th Gen, 8 GB RAM).

---

## 1. Prerequisites

1. **Operating System**: Windows 10 or Windows 11 (64-bit).
2. **Python**: Python 3.10, 3.11, or 3.12 (64-bit). Ensure **"Add Python to PATH"** is checked during installation.
3. **Hardware**:
   - Working Microphone (internal laptop mic or USB mic)
   - Working Speakers / Audio Output
   - 8 GB RAM (or higher)
   - Intel Core i3 / i5 / i7 or AMD Ryzen CPU
4. **Git**: Git for Windows installed.

---

## 2. Step-by-Step Setup

### Step 1: Clone the Repository
Open PowerShell or Command Prompt:

```powershell
git clone https://github.com/Infantorex/myoneAI.git
cd myoneAI
```

### Step 2: Create Virtual Environment
Create an isolated Python environment:

```powershell
python -m venv .venv
```

Activate the virtual environment:

```powershell
# In PowerShell:
.venv\Scripts\Activate.ps1

# Or in Command Prompt:
.venv\Scripts\activate.bat
```

### Step 3: Install Production Dependencies
Install the lightweight, non-heavy dependencies:

```powershell
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Copy the template configuration:

```powershell
copy .env.example .env
```

Open `.env` in Notepad and add your cloud API keys (e.g. Gemini, OpenAI, or Groq):

```ini
AI_PROVIDER=gemini
AI_API_KEY=AIzaSy...your_real_key_here
AI_MODEL=gemini-1.5-flash
```

*(Note: If no API key is provided, myoneAI falls back to safe deterministic rule-based processing for offline operation).*

### Step 5: Run Pre-Flight Diagnostics
Validate the installation:

```powershell
python -m app.core.health
```

All subsystems should display `PASS`.

### Step 6: Start JARVIS
Launch the voice assistant:

```powershell
# Using the Windows batch launcher:
scripts\start_myoneai.bat

# Or directly in Python:
python -m app.voice.jarvis
```

Say **"JARVIS"** or **"ஜார்விஸ்"** to begin speaking!
