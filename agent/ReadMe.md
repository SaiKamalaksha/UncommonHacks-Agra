# AGRA Agent

This folder contains the Windows file-watching agent. For full project setup, start with the root `README.md`.

## Run From Source

From the repo root:

```powershell
.\.venv\Scripts\activate
python -m agent.main
```

The agent watches:

- `%USERPROFILE%\Downloads`
- `%USERPROFILE%\Desktop`
- `C:\watched_folder`

## Build The EXE

From the repo root:

```powershell
.\.venv\Scripts\activate
cd agent
pyinstaller AgraSecurity.spec
```

The built executable is:

```text
agent\dist\AgraSecurity.exe
```

The current build uses a visible console for demos and also writes:

```text
agent\dist\AgraSecurity.log
```

## Demo Test

Create the harmless AGRA test file:

```powershell
Set-Content C:\watched_folder\agra_visible_test.txt "AGRA-EDR-TEST-MALWARE"
```

Expected output:

```text
[DETECT] New file: C:\watched_folder\agra_visible_test.txt
[SCAN] Scoring agra_visible_test.txt ...
[TEST] AGRA test signature detected.
[RESULT] agra_visible_test.txt: score=100, class=malicious
[BLOCK] STOPPED THREAT - deleted file: C:\watched_folder\agra_visible_test.txt
```

## Files

```text
main.py            entry point and logging
agent.py           watchdog worker and blocking/deletion
scorer.py          model loading, scoring, test signatures
alerter.py         POSTs alerts to backend
config.py          watched folders, thresholds, backend URL
AgraSecurity.spec  PyInstaller build config
```
