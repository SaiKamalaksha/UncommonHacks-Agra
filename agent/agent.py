import os
import queue
import threading
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from agent.alerter import Alerter
from agent.config import AgentConfig
from agent.llm_analyst import LLMAnalyst
from agent.scorer import Scorer


class _ScanHandler(FileSystemEventHandler):
    """Enqueues new/modified files that match configured extensions."""

    def __init__(self, config: AgentConfig, scan_queue: queue.Queue):
        super().__init__()
        self.extensions = set(ext.lower() for ext in config.scan_extensions)
        self.max_bytes = config.max_file_size_mb * 1024 * 1024
        self.scan_queue = scan_queue

    def _should_scan(self, path: str) -> bool:
        p = Path(path)
        if not p.is_file():
            return False
        if p.suffix.lower() not in self.extensions:
            return False
        if p.stat().st_size > self.max_bytes:
            return False
        return True

    def on_created(self, event):
        if not event.is_directory and self._should_scan(event.src_path):
            print(f"  [DETECT] New file: {event.src_path}")
            self.scan_queue.put(event.src_path)

    def on_modified(self, event):
        if not event.is_directory and self._should_scan(event.src_path):
            print(f"  [DETECT] Modified file: {event.src_path}")
            self.scan_queue.put(event.src_path)


class FileWatcher:
    """Watches configured directories and dispatches scan jobs to a worker thread."""

    def __init__(
        self,
        config: AgentConfig,
        scorer: Scorer,
        llm: LLMAnalyst | None,
        alerter: Alerter,
    ):
        self.config = config
        self.scorer = scorer
        self.llm = llm
        self.alerter = alerter
        self.scan_queue: queue.Queue = queue.Queue()
        self._observer = Observer()
        self._worker_thread: threading.Thread | None = None

    def start(self):
        handler = _ScanHandler(self.config, self.scan_queue)

        for watch_dir in self.config.watch_dirs:
            abs_dir = os.path.expanduser(watch_dir)
            if not os.path.isdir(abs_dir):
                print(f"  [WARN] Watch directory does not exist: {abs_dir}")
                continue
            self._observer.schedule(handler, abs_dir, recursive=False)
            print(f"  [WATCH] Monitoring: {abs_dir}")

        self._observer.start()

        self._worker_thread = threading.Thread(target=self._worker, daemon=True)
        self._worker_thread.start()

    def stop(self):
        self._observer.stop()
        self._observer.join()

    def _worker(self):
        while True:
            filepath = self.scan_queue.get()
            try:
                print(f"\n  [SCAN] Scoring {Path(filepath).name} ...")
                result = self.scorer.score_file(filepath)
                print(
                    f"  [RESULT] {result.filename}: "
                    f"score={result.threat_score}, class={result.classification}"
                )

                if self.llm and self.llm.available:
                    print("  [LLM] Requesting threat analysis ...")
                    result.llm_analysis = self.llm.analyze(result)
                    if result.llm_analysis:
                        print(f"  [LLM] {result.llm_analysis[:120]}...")

                sent = self.alerter.send_alert(result)
                if sent:
                    print(f"  [ALERT] Sent to backend.")
                else:
                    print(f"  [ALERT] Failed to send to backend.")
            except Exception as e:
                print(f"  [ERROR] Scanning {filepath}: {e}")
            finally:
                self.scan_queue.task_done()
