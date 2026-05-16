# Agra Security — Agent Setup

## Prerequisites
- Windows 10/11
- Python 3.10+
- Git

## Installation

### 1. Clone the repo
```powershell
git clone https://github.com/SaiKamalaksha/UncommonHacks-Agra.git
cd UncommonHacks-Agra/agent
```

### 2. Create and activate virtual environment
```powershell
python -m venv venv
.\venv\Scripts\activate
```

### 3. Install dependencies
```powershell
pip install watchdog requests plyer pystray Pillow
```

### 4. Create watched folder
```powershell
New-Item -ItemType Directory -Path "C:/watched_folder"
```

## Running the Agent

### Start the agent
```powershell
cd agent
.\venv\Scripts\activate
python main.py
```

You should see:
```
[Agra Security] Starting agent...
[DEBUG] Username: YourUsername
[DEBUG] C:/Users/YourUsername/Downloads exists: True
[DEBUG] C:/Users/YourUsername/Desktop exists: True
[DEBUG] C:/watched_folder exists: True
[WATCHING] C:/Users/YourUsername/Downloads
[WATCHING] C:/Users/YourUsername/Desktop
[WATCHING] C:/watched_folder
```

A green shield icon will appear in your system tray confirming the agent is running.

## Configuration

All settings are in `config.py`:

| Setting | Default | Description |
|---|---|---|
| `WATCHED_PATHS` | Downloads, Desktop, C:/watched_folder | Folders monitored by the agent |
| `WATCHED_EXTENSIONS` | .exe .dll .msi .bat .ps1 | File types that get scanned |
| `MALICIOUS_THRESHOLD` | 0.7 | Score above which a file is deleted |
| `SUSPICIOUS_THRESHOLD` | 0.4 | Score above which a file is flagged |
| `BACKEND_URL` | http://localhost:5000 | URL of the backend server |

To point the agent at the live backend, update `BACKEND_URL` in `config.py`:
```python
BACKEND_URL = "http://YOUR_NGROK_URL_HERE"
```

## Testing

### Start mock backend (separate terminal)
```powershell
python mock_backend.py
```

### Drop test files
```powershell
New-Item -ItemType File -Path "C:/watched_folder/ransomware_sample.exe"
New-Item -ItemType File -Path "C:/watched_folder/suspicious_tool.exe"
New-Item -ItemType File -Path "C:/watched_folder/notepad_backup.exe"
```

### Expected output
```
[DETECTED] C:/watched_folder/ransomware_sample.exe
[SCORED] ransomware_sample.exe → malicious (0.95)
[ALERT SENT] ransomware_sample.exe → malicious (0.95)
[DELETED] C:/watched_folder/ransomware_sample.exe
```

## File Structure
```
agent/
├── main.py          # entry point, file watcher
├── scorer.py        # scoring logic, model integration
├── alerter.py       # sends alerts to backend
├── config.py        # all configuration
├── tray_icon.py     # system tray icon
└── mock_backend.py  # local backend for testing
```

## Verdicts

| Verdict | Score Range | Action |
|---|---|---|
| Benign | 0.0 — 0.4 | No action, alert logged |
| Suspicious | 0.4 — 0.7 | Popup warning, alert logged |
| Malicious | 0.7 — 1.0 | File deleted, popup warning, alert logged |

## Troubleshooting

| Problem | Fix |
|---|---|
| No output when file dropped | Verify watched path exists and matches config.py |
| Alert failed — backend unreachable | Start mock_backend.py or update BACKEND_URL |
| Popup not showing | Run `pip install plyer` again |
| File not deleted | Check write permissions on watched folder |
| PIL not found | Run `pip install Pillow` |