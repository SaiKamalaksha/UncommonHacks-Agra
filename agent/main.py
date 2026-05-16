import os
import time
import threading
import hashlib
from datetime import datetime, timezone

import pystray
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from config import WATCHED_PATHS, WATCHED_EXTENSIONS, APP_NAME, USERNAME
from scorer import score_file, get_verdict, get_hash
from alerter import send_alert
from tray_icon import create_icon

# ── popup notification ───────────────────────────────────────────────
def show_popup(filename: str, verdict: str, score: float):
    try:
        from plyer import notification
        if verdict == "malicious":
            title = "⚠️ Threat Detected"
            message = f"{filename} was blocked (score: {score:.0%})"
        elif verdict == "suspicious":
            title = "⚠️ Suspicious File"
            message = f"{filename} flagged for review (score: {score:.0%})"
        else:
            return
        notification.notify(
            title=title,
            message=message,
            app_name=APP_NAME,
            timeout=5
        )
    except Exception as e:
        print(f"[POPUP ERROR] {e}")

# ── file deletion ────────────────────────────────────────────────────
def delete_file(filepath: str):
    try:
        os.remove(filepath)
        print(f"[DELETED] {filepath}")
    except Exception as e:
        print(f"[DELETE ERROR] {e}")

# ── file stability check ─────────────────────────────────────────────
def wait_for_file(filepath: str, timeout: int = 10) -> bool:
    size1 = -1
    start = time.time()
    while time.time() - start < timeout:
        try:
            size2 = os.path.getsize(filepath)
            if size2 == size1 and size2 > 0:
                return True
            size1 = size2
            time.sleep(0.5)
        except:
            time.sleep(0.5)
    return False

# ── file extension check ─────────────────────────────────────────────
def should_scan(filepath: str) -> bool:
    return any(filepath.lower().endswith(ext) for ext in WATCHED_EXTENSIONS)

# ── core handler ─────────────────────────────────────────────────────
class MalwareWatcher(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        filepath = event.src_path
        if not should_scan(filepath):
            return
        thread = threading.Thread(
            target=self.process_file,
            args=(filepath,),
            daemon=True
        )
        thread.start()

    def process_file(self, filepath: str):
        print(f"[DETECTED] {filepath}")

        if not wait_for_file(filepath):
            print(f"[SKIPPED] File unstable: {filepath}")
            return

        filename = os.path.basename(filepath)
        file_hash = get_hash(filepath)
        score = score_file(filepath)
        verdict = get_verdict(score)

        print(f"[SCORED] {filename} → {verdict} ({score:.2f})")

        alert = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "filename": filename,
            "filepath": filepath,
            "threat_score": round(score, 4),
            "verdict": verdict,
            "file_hash": file_hash
        }

        send_alert(alert)
        show_popup(filename, verdict, score)

        if verdict == "malicious":
            delete_file(filepath)

# ── tray ─────────────────────────────────────────────────────────────
def build_tray(observer):
    def on_quit(icon, item):
        print("[AGRA] Shutting down...")
        observer.stop()
        icon.stop()

    icon = pystray.Icon(
        name="AgraSecurity",
        icon=create_icon("green"),
        title="Agra Security — Protected",
        menu=pystray.Menu(
            pystray.MenuItem("Agra Security — Running", None, enabled=False),
            pystray.MenuItem("Quit", on_quit)
        )
    )
    return icon

# ── entry point ──────────────────────────────────────────────────────
def main():
    print(f"[{APP_NAME}] Starting agent...")
    print(f"[DEBUG] Username: {USERNAME}")

    observer = Observer()
    for path in WATCHED_PATHS:
        if os.path.exists(path):
            observer.schedule(MalwareWatcher(), path=path, recursive=False)
            print(f"[WATCHING] {path}")
        else:
            print(f"[SKIPPED] Path not found: {path}")

    for path in WATCHED_PATHS:
        print(f"[DEBUG] {path} exists: {os.path.exists(path)}")

    observer.start()

    icon = build_tray(observer)
    icon.run()

    observer.join()

if __name__ == "__main__":
    main()