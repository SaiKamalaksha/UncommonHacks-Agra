import os
import queue
import time
import threading
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from agent.alerter import Alerter
from agent.config import AgentConfig
from agent.llm_analyst import LLMAnalyst
from agent.scorer import Scorer
from agent.status import StatusStore

_SEEN_MAX = 10_000  # max debounce entries before evicting oldest


class _ScanHandler(FileSystemEventHandler):
    """Enqueues new/modified files that match configured extensions."""

    # Browser temp extensions to ignore (file not fully written yet)
    _TEMP_EXTS = {".crdownload", ".part", ".tmp", ".download", ".partial", ".opdownload"}

    def __init__(self, config: AgentConfig, scan_queue: queue.Queue):
        super().__init__()
        self.extensions = set(ext.lower() for ext in config.scan_extensions)
        self.max_bytes = config.max_file_size_mb * 1024 * 1024
        self.scan_queue = scan_queue
        self._seen: OrderedDict = OrderedDict()

    def _should_scan(self, path: str) -> bool:
        p = Path(path)
        if not p.is_file():
            return False
        if p.suffix.lower() in self._TEMP_EXTS:
            return False
        if p.suffix.lower() not in self.extensions:
            return False
        try:
            size = p.stat().st_size
            if size == 0 or size > self.max_bytes:
                return False
        except OSError:
            return False
        # Debounce: ignore same file within 5 seconds
        now = time.time()
        if now - self._seen.get(path, 0) < 5:
            return False
        self._seen[path] = now
        # Evict oldest entries once the dict exceeds the size cap
        while len(self._seen) > _SEEN_MAX:
            self._seen.popitem(last=False)
        return True

    def on_created(self, event):
        if not event.is_directory and self._should_scan(event.src_path):
            print(f"  [DETECT] New file: {event.src_path}")
            self.scan_queue.put(event.src_path)

    def on_modified(self, event):
        if not event.is_directory and self._should_scan(event.src_path):
            print(f"  [DETECT] Modified file: {event.src_path}")
            self.scan_queue.put(event.src_path)

    def on_moved(self, event):
        """Catches browser downloads: they write to .crdownload/.part then rename."""
        if not event.is_directory and self._should_scan(event.dest_path):
            print(f"  [DETECT] Download complete: {Path(event.dest_path).name}")
            self.scan_queue.put(event.dest_path)


class FileWatcher:
    """Watches configured directories and dispatches scan jobs to a thread pool."""

    def __init__(
        self,
        config: AgentConfig,
        scorer: Scorer,
        llm: Optional[LLMAnalyst],
        alerter: Alerter,
        status: Optional[StatusStore] = None,
    ):
        self.config = config
        self.scorer = scorer
        self.llm = llm
        self.alerter = alerter
        self.status = status
        self.scan_queue: queue.Queue = queue.Queue()
        self._observer = Observer()
        self._worker_thread: Optional[threading.Thread] = None
        # Thread pool: LLM calls can block up to 30 s, so parallel workers
        # keep throughput high when multiple files arrive simultaneously.
        self._executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="agra-scan")

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
        self._executor.shutdown(wait=False)

    def _worker(self):
        """Dispatch queue items to the thread pool; actual scanning runs in _scan_one."""
        while True:
            filepath = self.scan_queue.get()
            self._executor.submit(self._scan_one, filepath)

    def _scan_one(self, filepath: str):
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

            # Send alert to backend before deleting — ensures a record exists
            # even if deletion fails or the backend goes offline afterward.
            sent = self.alerter.send_alert(result)
            if sent:
                print(f"  [ALERT] Sent to backend.")
            else:
                print(f"  [ALERT] Failed to send to backend.")

            deleted = False
            if result.threat_score >= self.config.threat_threshold:
                try:
                    os.remove(filepath)
                    deleted = True
                    print(f"  [BLOCK] STOPPED THREAT - deleted file: {filepath}")
                except FileNotFoundError:
                    print(f"  [BLOCK] File already removed: {filepath}")
                except Exception as e:
                    print(f"  [BLOCK] Failed to delete {filepath}: {e}")

            if self.status is not None:
                self.status.record_scan(result, deleted=deleted, alert_sent=sent)
        except Exception as e:
            print(f"  [ERROR] Scanning {filepath}: {e}")
        finally:
            self.scan_queue.task_done()
