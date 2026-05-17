# AGRA - AI-Powered Endpoint Detection & Response

AGRA is a lightweight local EDR prototype. It watches common download locations, scores new files with ML models trained around EMBER-style features, sends alerts to a FastAPI backend, and shows results in a React dashboard.

The current demo agent is intentionally built with a visible console so teammates can see detection, scoring, and deletion happen live.

## Prerequisites

- Windows 10/11
- Python 3.10+ recommended
- Node.js 18+ and npm
- Git
- Ollama, optional but recommended for local LLM analysis

## Setup

### 1. Clone

```powershell
git clone https://github.com/SaiKamalaksha/UncommonHacks-Agra.git
cd UncommonHacks-Agra
```

### 2. Create a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
```

### 3. Install Python dependencies

```powershell
pip install -r requirements.txt
```

### 4. Install `thrember`

`thrember` is not published on PyPI. Install it from the EMBER2024 repo:

```powershell
git submodule update --init --recursive

# If EMBER2024 is still missing, use:
# git clone https://github.com/FutureComputing4AI/EMBER2024.git

cd EMBER2024
pip install .
cd ..
```

### 5. Create the demo watch folder

```powershell
New-Item -ItemType Directory -Force C:\watched_folder
```

### 6. Optional: start Ollama

```powershell
ollama pull qwen2.5:0.5b
ollama serve
```

If Ollama is not running, the agent still works in ML-only mode.

## Running Locally

### Backend

```powershell
.\.venv\Scripts\activate
uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
```

### Agent, visible console mode

```powershell
.\.venv\Scripts\activate
python -m agent.main
```

The agent watches:

- `%USERPROFILE%\Downloads`
- `%USERPROFILE%\Desktop`
- `C:\watched_folder`

Logs are also written to:

```text
agent\AgraSecurity.log
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal, usually `http://localhost:5173`.

## Building The Windows Agent EXE

The PyInstaller spec is in `agent/AgraSecurity.spec`.

```powershell
.\.venv\Scripts\activate
cd agent
pyinstaller AgraSecurity.spec
```

The executable is created at:

```text
agent\dist\AgraSecurity.exe
```

This build currently uses `console=True` so detections are visible during demos. Runtime logs are written beside the exe:

```text
agent\dist\AgraSecurity.log
```

## Testing Detection And Deletion

Use the harmless built-in AGRA test signature:

```powershell
Set-Content C:\watched_folder\agra_visible_test.txt "AGRA-EDR-TEST-MALWARE"
```

Expected agent output:

```text
[DETECT] New file: C:\watched_folder\agra_visible_test.txt
[SCAN] Scoring agra_visible_test.txt ...
[TEST] AGRA test signature detected.
[RESULT] agra_visible_test.txt: score=100, class=malicious
[BLOCK] STOPPED THREAT - deleted file: C:\watched_folder\agra_visible_test.txt
```

You can also test with the official EICAR antivirus test file. Windows Defender may delete EICAR before AGRA sees it, so the AGRA test signature is the easiest demo path.

## Important Runtime Notes

- Files with score `>= 70` are deleted.
- Password-protected/encrypted ZIP files are blocked because their contents cannot be inspected.
- The packaged agent uses hidden imports in `AgraSecurity.spec` so pickled scikit-learn/HDBSCAN models load correctly.
- The login window falls back to the dummy test login if Tkinter is unavailable in the local Python install.

Dummy test credentials:

```text
email: test@agra.com
password: agra1234
```

## Project Structure

```text
UncommonHacks-Agra/
  agent/                 Windows file-watching agent
    main.py              Agent entry point
    agent.py             Watchdog queue and delete/block logic
    scorer.py            ML scoring and safe test signatures
    AgraSecurity.spec    PyInstaller build config
  backend/               FastAPI alert API and SQLite storage
  frontend/              React dashboard
  model/                 Trained model files
  pipeline.py            Older all-in-one pipeline entry point
  requirements.txt       Python dependencies
```
