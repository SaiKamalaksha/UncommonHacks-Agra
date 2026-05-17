import signal
import sys
import traceback
from pathlib import Path
from agent.alerter import Alerter
from agent.agent import FileWatcher
from agent.config import AgentConfig
from agent.llm_analyst import LLMAnalyst
from agent.scorer import Scorer
from agent.permissions import check_folder_access
from agent.auth import save_token, load_token
from agent.login_window import LoginWindow
from agent.tray_icon import build_tray

# shared stats for tray
stats = {"blocked": 0, "scanned": 0}
_lock_file = None

class Tee:
    def __init__(self, *streams):
        self.streams = [stream for stream in streams if stream is not None]

    def write(self, data):
        for stream in self.streams:
            stream.write(data)
            stream.flush()

    def flush(self):
        for stream in self.streams:
            stream.flush()

def setup_logging():
    if getattr(sys, "frozen", False):
        log_path = Path(sys.executable).with_name("AgraSecurity.log")
    else:
        log_path = Path(__file__).with_name("AgraSecurity.log")

    log_file = open(log_path, "a", encoding="utf-8", buffering=1)
    sys.stdout = Tee(sys.__stdout__, log_file)
    sys.stderr = Tee(sys.__stderr__, log_file)
    print("\n" + "=" * 60)
    print(f"AGRA startup log: {log_path}")

def already_running() -> bool:
    if not sys.platform.startswith("win"):
        return False

    import msvcrt

    global _lock_file
    if getattr(sys, "frozen", False):
        lock_path = Path(sys.executable).with_name("AgraSecurity.lock")
    else:
        lock_path = Path(__file__).with_name("AgraSecurity.lock")

    _lock_file = open(lock_path, "w")
    try:
        msvcrt.locking(_lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        _lock_file.write(str(Path(sys.executable if getattr(sys, "frozen", False) else __file__)))
        _lock_file.flush()
        return False
    except OSError:
        return True

def main():
    setup_logging()

    if already_running():
        print("[AGRA] Another instance is already running. Exiting.")
        return

    print("=" * 60)
    print("  AGRA EDR Agent")
    print("=" * 60)

    # step 1 - check folder permissions
    print("\n[0/4] Checking folder permissions ...")
    check_folder_access()

    # step 2 - login check
    token = load_token()
    if not token:
        print("\n[AUTH] No saved session, showing login...")
        login = LoginWindow()
        token = login.run()
        if not token:
            print("[AUTH] Login cancelled, exiting.")
            sys.exit(1)
        save_token(token)
    else:
        print("\n[AUTH] Session restored, skipping login.")

    # step 3 - load models
    config = AgentConfig()
    print("\n[1/4] Loading ML models ...")
    scorer = Scorer(config.model_dir)

    llm = None
    if config.use_llm:
        print("\n[2/4] Connecting to Ollama LLM ...")
        llm = LLMAnalyst(config.ollama_model, config.ollama_url)
        if llm.available:
            print(f"  Ollama connected — model: {config.ollama_model}")
        else:
            print("  Ollama not available — running ML-only mode.")
    else:
        print("\n[2/4] LLM disabled in config — ML-only mode.")

    print("\n[3/4] Initializing alerter ...")
    alerter = Alerter(config)
    
    # patch alerter to update stats
    original_send = alerter.send_alert
    def patched_send(result):
        stats["scanned"] += 1
        if result.classification == "malicious":
            stats["blocked"] += 1
        return original_send(result)
    alerter.send_alert = patched_send

    print(f"  Backend: {config.backend_url}")

    print("\n[4/4] Starting file watcher ...")
    watcher = FileWatcher(config, scorer, llm, alerter)
    watcher.start()

    print("\n" + "=" * 60)
    print("  Agent is running — hidden in system tray.")
    print("=" * 60 + "\n")

    # step 4 - shutdown handler
    def shutdown(signum, frame):
        print("\n  Shutting down ...")
        watcher.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, shutdown)

    # step 5 - run tray icon in main thread, watcher runs in background
    icon = build_tray(watcher, stats)
    icon.run()

if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise
