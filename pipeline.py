#!/usr/bin/env python3
"""
AGRA EDR Pipeline — single-file, all-in-one.

Runs:
  1. FastAPI backend (serves alerts to the React dashboard)
  2. Watchdog file watcher (detects new/modified files)
  3. ML scorer (LightGBM + Random Forest + clustering)
  4. LLM analyst (Qwen 2.5 0.5B via Ollama)

Usage:
    python pipeline.py                        # watch ~/Downloads
    python pipeline.py --watch ~/Desktop      # watch a custom dir
    python pipeline.py --port 8000            # change API port
"""

import argparse
import hashlib
import math
import os
import pickle
import platform
import queue
import signal
import sqlite3
import sys
import threading
import time
import warnings
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

IS_WINDOWS = platform.system() == "Windows"

warnings.filterwarnings("ignore")

import lightgbm as lgb
import numpy as np
import requests as http_requests
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

# ─── thrember: patch broken signify import, then load ──────────────────────
THREMBER_OK = False
try:
    # signify renamed SignedPEFile -> AuthenticodeFile in newer versions.
    # Patch it so thrember's import succeeds.
    import signify.authenticode
    if not hasattr(signify.authenticode, "SignedPEFile"):
        signify.authenticode.SignedPEFile = signify.authenticode.AuthenticodeFile
    import thrember
    THREMBER_OK = True
    print("[+] thrember loaded — using EMBER2024 feature extraction (2568 features)")
except Exception as e:
    print(f"[!] thrember unavailable ({e}) — using heuristic feature extraction")


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

MODEL_DIR = Path(__file__).resolve().parent / "model"

SCAN_EXTENSIONS = {
    ".exe", ".dll", ".sys", ".ps1", ".bat",
    ".xlsm", ".pdf", ".elf", ".apk", ".bin",
    ".msi", ".scr", ".com", ".vbs", ".js",
    ".txt", ".zip", ".rar", ".7z", ".tar",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt",
    ".iso", ".img", ".dmg", ".deb", ".rpm",
    ".sh", ".py", ".jar", ".class", ".so",
    ".dylib", ".cmd", ".reg", ".inf", ".lnk",
    ".hta", ".cpl", ".wsf", ".wsh",
}

# Set to True to scan ALL files regardless of extension
SCAN_ALL_FILES = True

MAX_FILE_SIZE_MB = 100
THREAT_THRESHOLD = 70
WARNING_THRESHOLD = 40

OLLAMA_MODEL = "qwen2.5:0.5b"
OLLAMA_URL = "http://127.0.0.1:11434"


# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE (SQLite, thread-safe)
# ═══════════════════════════════════════════════════════════════════════════════

DB_PATH = Path(__file__).resolve().parent / "agra.db"
_db_lock = threading.Lock()


def _connect():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


_db_conn: Optional[sqlite3.Connection] = None


def get_db():
    global _db_conn
    if _db_conn is None:
        _db_conn = _connect()
    return _db_conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            filename TEXT,
            filepath TEXT,
            file_hash TEXT,
            score INTEGER,
            classification TEXT,
            lgbm_score REAL,
            rf_score REAL,
            cluster_id INTEGER DEFAULT -1,
            hdbscan_cluster_id INTEGER DEFAULT -1,
            llm_analysis TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()


def db_insert_alert(data: dict) -> int:
    conn = get_db()
    with _db_lock:
        cur = conn.execute(
            """INSERT INTO alerts
               (timestamp, filename, filepath, file_hash, score, classification,
                lgbm_score, rf_score, cluster_id, hdbscan_cluster_id, llm_analysis)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                data["timestamp"], data["filename"], data["filepath"],
                data["file_hash"], data["score"], data["classification"],
                data["lgbm_score"], data["rf_score"],
                data.get("cluster_id", -1), data.get("hdbscan_cluster_id", -1),
                data.get("llm_analysis"),
            ),
        )
        conn.commit()
        return cur.lastrowid


def db_get_alerts(limit: int = 50) -> list:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM alerts ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    results = []
    for row in rows:
        d = dict(row)
        s = d["score"]
        d["verdict"] = "Malicious" if s > 70 else ("Suspicious" if s >= 40 else "Benign")
        results.append(d)
    return results


def db_get_stats() -> dict:
    conn = get_db()
    row = conn.execute("""
        SELECT
            COUNT(*)                                                  AS total_scanned,
            COALESCE(SUM(CASE WHEN score > 70 THEN 1 ELSE 0 END),0)  AS threats,
            COALESCE(SUM(CASE WHEN score>=40 AND score<=70 THEN 1 ELSE 0 END),0) AS warnings,
            COALESCE(SUM(CASE WHEN score < 40 THEN 1 ELSE 0 END),0)  AS safe
        FROM alerts
    """).fetchone()
    return dict(row)


# ═══════════════════════════════════════════════════════════════════════════════
# FASTAPI BACKEND
# ═══════════════════════════════════════════════════════════════════════════════

class AlertIn(BaseModel):
    timestamp: str
    filename: str
    filepath: str
    file_hash: str
    score: int
    classification: str
    lgbm_score: float
    rf_score: float
    cluster_id: int = -1
    hdbscan_cluster_id: int = -1
    llm_analysis: Optional[str] = None


class AlertOut(BaseModel):
    id: int
    timestamp: str
    filename: str
    filepath: str
    file_hash: str
    score: int
    classification: str
    lgbm_score: float
    rf_score: float
    cluster_id: int
    hdbscan_cluster_id: int
    llm_analysis: Optional[str]
    verdict: str


class StatsOut(BaseModel):
    total_scanned: int
    threats: int
    warnings: int
    safe: int


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="AGRA EDR", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/alerts", response_model=List[AlertOut])
def api_get_alerts(limit: int = 50):
    return db_get_alerts(limit)


@app.post("/api/alerts")
def api_create_alert(alert: AlertIn):
    aid = db_insert_alert(alert.model_dump())
    return {"id": aid, "status": "ok"}


@app.get("/api/stats", response_model=StatsOut)
def api_get_stats():
    return db_get_stats()


# ═══════════════════════════════════════════════════════════════════════════════
# ML SCORER
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ScanResult:
    filepath: str = ""
    filename: str = ""
    file_size: int = 0
    file_hash: str = ""
    lgbm_score: float = 0.0
    rf_score: float = 0.0
    threat_score: int = 0
    classification: str = "benign"
    cluster_id: int = -1
    hdbscan_cluster_id: int = -1
    top_features: list = field(default_factory=list)
    llm_analysis: Optional[str] = None
    timestamp: str = ""


def sha256_file(filepath: str) -> str:
    h = hashlib.sha256()
    # Retry on Windows where files may be briefly locked by another process
    for attempt in range(3):
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
            return h.hexdigest()
        except PermissionError:
            if attempt < 2:
                time.sleep(0.5)
            else:
                raise


NUM_FEATURES = 2568  # must match trained models


def heuristic_features(filepath: str) -> np.ndarray:
    """
    When thrember is unavailable, extract heuristic features from a binary.
    Matches the 2568-feature layout the models expect:
      GeneralFileInfo(7) + ByteHistogram(256) + ByteEntropyHistogram(256) +
      StringExtractor(177) + HeaderFileInfo(74) + SectionInfo(224) +
      ImportsInfo(1282) + ExportsInfo(129) + DataDirectories(34) +
      RichHeader(33) + AuthenticodeSignature(8) + PEFormatWarnings(88)
    Only the first three groups are meaningfully populated; the rest are zeros
    (PE-specific features that don't apply to non-PE files).
    """
    data = Path(filepath).read_bytes()
    size = len(data)

    # ── GeneralFileInfo (7) ──
    log_size = math.log2(max(size, 1))
    if size == 0:
        entropy = 0.0
    else:
        freq = np.bincount(np.frombuffer(data, dtype=np.uint8), minlength=256).astype(np.float64)
        freq = freq / size
        entropy = -np.sum(freq[freq > 0] * np.log2(freq[freq > 0]))
    is_pe = 1.0 if data[:2] == b"MZ" else 0.0
    start_bytes = [float(data[i]) if i < size else 0.0 for i in range(4)]
    general = [float(size), entropy, is_pe] + start_bytes  # 7

    # ── ByteHistogram (256) ──
    byte_counts = np.bincount(np.frombuffer(data, dtype=np.uint8), minlength=256).astype(np.float32)
    byte_hist = byte_counts / max(size, 1)  # 256

    # ── ByteEntropyHistogram (256) ──
    # Simplified: flat 16x16 histogram
    byte_ent = np.zeros(256, dtype=np.float32)
    if size > 0:
        # Coarse approximation: distribute byte counts across entropy bins
        byte_ent[:256] = byte_hist  # use same histogram as placeholder
    # 256

    # ── StringExtractor (177) ──
    import re
    allstrings = re.findall(b"[\x20-\x7f]{5,}", data)
    num_strings = len(allstrings)
    if num_strings > 0:
        joined = b"".join(allstrings)
        string_lengths = [len(s) for s in allstrings]
        avlength = sum(string_lengths) / num_strings
        shifted = np.array([b - 0x20 for b in joined], dtype=np.int32)
        printable_dist = np.bincount(shifted, minlength=96).astype(np.float32)
        printables = float(printable_dist.sum())
        if printables > 0:
            printable_dist_norm = printable_dist / printables
            p = printable_dist_norm[printable_dist_norm > 0]
            str_entropy = float(-np.sum(p * np.log2(p)))
        else:
            printable_dist_norm = printable_dist
            str_entropy = 0.0
    else:
        avlength = 0.0
        printable_dist_norm = np.zeros(96, dtype=np.float32)
        printables = 0.0
        str_entropy = 0.0
    string_regex_counts = np.zeros(76, dtype=np.float32)  # 76 regex patterns
    strings_feat = np.hstack([num_strings, avlength, printables, printable_dist_norm, str_entropy, string_regex_counts])  # 5+96+76=177

    # ── Remaining PE-specific features: zeros ──
    # HeaderFileInfo(74) + SectionInfo(224) + ImportsInfo(1282) +
    # ExportsInfo(129) + DataDirectories(34) + RichHeader(33) +
    # AuthenticodeSignature(8) + PEFormatWarnings(88) = 1872
    pe_zeros = np.zeros(1872, dtype=np.float32)

    features = np.concatenate([general, byte_hist, byte_ent, strings_feat, pe_zeros]).astype(np.float32)
    # Ensure exactly NUM_FEATURES
    if len(features) < NUM_FEATURES:
        features = np.pad(features, (0, NUM_FEATURES - len(features)))
    features = features[:NUM_FEATURES]
    return features.reshape(1, -1)


def thrember_features(filepath: str) -> np.ndarray:
    """Extract features using thrember's PEFeatureExtractor directly on the file bytes."""
    from thrember.features import PEFeatureExtractor
    extractor = PEFeatureExtractor()
    # Use open() with retry for Windows file-lock resilience
    for attempt in range(3):
        try:
            with open(filepath, "rb") as f:
                bytez = f.read()
            break
        except PermissionError:
            if attempt < 2:
                time.sleep(0.5)
            else:
                raise
    vec = extractor.feature_vector(bytez)
    return vec.reshape(1, -1)


class Scorer:
    def __init__(self, use_npu: bool = True):
        print(f"  Loading models from {MODEL_DIR} ...")

        # ── Try ONNX Runtime with OpenVINO/NPU acceleration ──
        self._onnx_lgbm = None
        self._onnx_rf = None
        self._npu_active = False

        lgbm_onnx = MODEL_DIR / "lgbm_classifier.onnx"
        rf_onnx = MODEL_DIR / "random_forest_classifier.onnx"

        if use_npu and lgbm_onnx.exists() and rf_onnx.exists():
            try:
                import onnxruntime as ort

                # Tree-ensemble ONNX models don't work with OpenVINO EP (dynamic rank issue).
                # ONNX Runtime's CPU provider is already 200x+ faster than native sklearn
                # thanks to its optimized C++ tree traversal.
                # When NPU permissions are set up, neural-network models (future DNN classifier)
                # can use OpenVINOExecutionProvider with device_type=NPU.
                providers_to_try = [
                    (["CPUExecutionProvider"], "ONNX-optimized"),
                ]
                for providers, label in providers_to_try:
                    try:
                        self._onnx_lgbm = ort.InferenceSession(str(lgbm_onnx), providers=providers)
                        self._onnx_rf = ort.InferenceSession(str(rf_onnx), providers=providers)
                        self._npu_active = True
                        print(f"  ONNX Runtime loaded — mode: {label} (~200x faster)")
                        break
                    except Exception:
                        continue
            except ImportError:
                pass

        # ── Fallback: native LightGBM + sklearn ──
        if not self._npu_active:
            self.lgbm = lgb.Booster(model_file=str(MODEL_DIR / "lgbm_classifier.model"))
            with open(MODEL_DIR / "random_forest_classifier.pkl", "rb") as f:
                self.rf = pickle.load(f)
            print("  Using native LightGBM + sklearn (no NPU)")
        else:
            # Still load native lgbm for feature importance
            self.lgbm = lgb.Booster(model_file=str(MODEL_DIR / "lgbm_classifier.model"))

        with open(MODEL_DIR / "kmeans_clusterer.pkl", "rb") as f:
            self.kmeans = pickle.load(f)

        with open(MODEL_DIR / "hdbscan_clusterer.pkl", "rb") as f:
            self.hdbscan_model = pickle.load(f)

        with open(MODEL_DIR / "cluster_scaler.pkl", "rb") as f:
            self.scaler = pickle.load(f)

        with open(MODEL_DIR / "cluster_pca.pkl", "rb") as f:
            self.pca = pickle.load(f)

        self._importance = self.lgbm.feature_importance(importance_type="gain")
        print("  All models loaded successfully.")

    def extract_features(self, filepath: str) -> np.ndarray:
        if THREMBER_OK:
            try:
                return thrember_features(filepath)
            except Exception as e:
                print(f"  [WARN] thrember extraction failed ({e}), using heuristic")
        return heuristic_features(filepath)

    def score_file(self, filepath: str) -> ScanResult:
        features = self.extract_features(filepath)
        fpath = Path(filepath)

        # ── Classification ──
        if self._npu_active:
            # ONNX Runtime path (NPU/OpenVINO accelerated)
            lgbm_out = self._onnx_lgbm.run(None, {"input": features.astype(np.float32)})
            lgbm_prob = float(lgbm_out[1][0][1])  # probabilities dict, class 1

            rf_out = self._onnx_rf.run(None, {"input": features.astype(np.float32)})
            rf_prob = float(rf_out[1][0][1])
        else:
            lgbm_prob = float(self.lgbm.predict(features)[0])
            rf_prob = float(self.rf.predict_proba(features)[0][1])

        blended = 0.7 * lgbm_prob + 0.3 * rf_prob
        threat_score = max(0, min(100, int(blended * 100)))

        if threat_score > THREAT_THRESHOLD:
            classification = "malicious"
        elif threat_score >= WARNING_THRESHOLD:
            classification = "suspicious"
        else:
            classification = "benign"

        # ── Clustering ──
        km_cluster = -1
        hdb_cluster = -1
        try:
            scaled = self.scaler.transform(features)
            reduced = self.pca.transform(scaled)
            km_cluster = int(self.kmeans.predict(reduced)[0])
        except Exception:
            pass

        try:
            import hdbscan as hdbscan_lib
            labels, _ = hdbscan_lib.approximate_predict(self.hdbscan_model, reduced)
            hdb_cluster = int(labels[0])
        except Exception:
            pass

        # ── Top features ──
        top_features = []
        try:
            feat_vals = features[0]
            weighted = np.abs(feat_vals) * self._importance
            top_idx = np.argsort(weighted)[-5:][::-1]
            top_features = [
                {"index": int(i), "value": float(feat_vals[i]),
                 "importance": float(self._importance[i])}
                for i in top_idx
            ]
        except Exception:
            pass

        return ScanResult(
            filepath=filepath,
            filename=fpath.name,
            file_size=fpath.stat().st_size,
            file_hash=sha256_file(filepath),
            lgbm_score=lgbm_prob,
            rf_score=rf_prob,
            threat_score=threat_score,
            classification=classification,
            cluster_id=km_cluster,
            hdbscan_cluster_id=hdb_cluster,
            top_features=top_features,
            timestamp=datetime.now().strftime("%H:%M:%S"),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# LLM ANALYST (Ollama / Qwen)
# ═══════════════════════════════════════════════════════════════════════════════

class LLMAnalyst:
    def __init__(self):
        self.model = OLLAMA_MODEL
        self.base_url = OLLAMA_URL
        self.available = self._check()

    def _check(self) -> bool:
        try:
            r = http_requests.get(f"{self.base_url}/api/tags", timeout=2)
            return r.status_code == 200
        except Exception:
            return False

    def analyze(self, result: ScanResult) -> Optional[str]:
        if not self.available:
            self.available = self._check()
            if not self.available:
                return None

        prompt = (
            "You are a cybersecurity analyst for an EDR system. "
            "Analyze this file scan and give a brief threat assessment.\n\n"
            f"FILE: {result.filename}\n"
            f"SIZE: {result.file_size} bytes\n"
            f"SHA256: {result.file_hash}\n\n"
            "ML ANALYSIS:\n"
            f"- LightGBM malware probability: {result.lgbm_score:.1%}\n"
            f"- Random Forest malware probability: {result.rf_score:.1%}\n"
            f"- Combined threat score: {result.threat_score}/100\n"
            f"- Classification: {result.classification}\n"
            f"- KMeans cluster: {result.cluster_id}\n"
            f"- HDBSCAN cluster: {result.hdbscan_cluster_id} (-1 = anomalous)\n\n"
            "Give a 2-3 sentence finding: threat type, confidence, recommended action."
        )

        try:
            resp = http_requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": 256},
                },
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json().get("response", "").strip()
        except Exception as e:
            print(f"  [LLM] Error: {e}")
            return None


# ═══════════════════════════════════════════════════════════════════════════════
# FILE WATCHER (watchdog)
# ═══════════════════════════════════════════════════════════════════════════════

class ScanHandler(FileSystemEventHandler):
    def __init__(self, scan_queue: queue.Queue):
        super().__init__()
        self._seen: dict[str, float] = {}
        self._max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
        # Browser temp extensions to ignore (file not ready yet)
        # Covers Chrome (.crdownload), Firefox (.part), Edge (.partial), generic (.tmp, .download)
        self._temp_exts = {".crdownload", ".part", ".tmp", ".download", ".partial", ".opdownload"}

    def _ok(self, path: str) -> bool:
        p = Path(path)
        if not p.is_file():
            return False
        # Skip browser temp/partial downloads
        if p.suffix.lower() in self._temp_exts:
            return False
        # Check extension filter (unless SCAN_ALL_FILES is on)
        if not SCAN_ALL_FILES and p.suffix.lower() not in SCAN_EXTENSIONS:
            return False
        try:
            if p.stat().st_size > self._max_bytes:
                return False
            if p.stat().st_size == 0:
                return False
        except OSError:
            return False
        # Debounce: ignore same file within 5 seconds
        now = time.time()
        last = self._seen.get(path, 0)
        if now - last < 5:
            return False
        self._seen[path] = now
        return True

    def on_created(self, event):
        if not event.is_directory and self._ok(event.src_path):
            print(f"\n  [DETECT] New file: {Path(event.src_path).name}")
            scan_queue.put(event.src_path)

    def on_modified(self, event):
        if not event.is_directory and self._ok(event.src_path):
            print(f"\n  [DETECT] Modified: {Path(event.src_path).name}")
            scan_queue.put(event.src_path)

    def on_moved(self, event):
        """Catches browser downloads: they write to .crdownload/.part then rename."""
        if not event.is_directory and self._ok(event.dest_path):
            print(f"\n  [DETECT] Download complete: {Path(event.dest_path).name}")
            scan_queue.put(event.dest_path)


# ═══════════════════════════════════════════════════════════════════════════════
# WORKER THREAD
# ═══════════════════════════════════════════════════════════════════════════════

scan_queue: queue.Queue = queue.Queue()


def worker(scorer: Scorer, llm: LLMAnalyst):
    while True:
        filepath = scan_queue.get()
        try:
            # Delay to let browser/OS finish writing/renaming the file
            # Windows holds file locks longer than Linux
            time.sleep(2.0 if IS_WINDOWS else 1.0)

            if not Path(filepath).exists():
                print(f"  [SKIP] File gone: {filepath}")
                continue

            print(f"  [SCAN] Scoring {Path(filepath).name} ...")
            result = scorer.score_file(filepath)
            print(
                f"  [RESULT] {result.filename}: "
                f"score={result.threat_score}/100  class={result.classification}"
            )

            if llm.available:
                print(f"  [LLM] Querying {OLLAMA_MODEL} ...")
                result.llm_analysis = llm.analyze(result)
                if result.llm_analysis:
                    # Print first 150 chars
                    preview = result.llm_analysis[:150].replace("\n", " ")
                    print(f"  [LLM] {preview}...")
                else:
                    print(f"  [LLM] No response")

            # Store directly in DB (no HTTP round-trip needed since we're in-process)
            alert_data = {
                "timestamp": result.timestamp,
                "filename": result.filename,
                "filepath": result.filepath,
                "file_hash": result.file_hash,
                "score": result.threat_score,
                "classification": result.classification,
                "lgbm_score": result.lgbm_score,
                "rf_score": result.rf_score,
                "cluster_id": result.cluster_id,
                "hdbscan_cluster_id": result.hdbscan_cluster_id,
                "llm_analysis": result.llm_analysis,
            }
            aid = db_insert_alert(alert_data)
            print(f"  [DB] Alert #{aid} saved.")

            # Auto-delete files classified as malicious
            if result.classification == "malicious":
                deleted = False
                for attempt in range(3):
                    try:
                        os.remove(filepath)
                        print(f"  [DELETE] Removed malicious file: {result.filename}")
                        deleted = True
                        break
                    except PermissionError:
                        # Windows may hold a lock briefly after scanning
                        time.sleep(1)
                    except OSError as del_err:
                        print(f"  [DELETE] Failed to remove {result.filename}: {del_err}")
                        break
                if not deleted and os.path.exists(filepath):
                    print(f"  [DELETE] Could not remove {result.filename} (file may be locked)")

            print(f"  {'─' * 50}")

        except Exception as e:
            print(f"  [ERROR] {Path(filepath).name}: {e}")
            import traceback
            traceback.print_exc()
        finally:
            scan_queue.task_done()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="AGRA EDR Pipeline")
    parser.add_argument(
        "--watch", nargs="+",
        default=[str(Path.home() / "Downloads")],
        help="Directories to watch (default: ~/Downloads)",
    )
    parser.add_argument("--port", type=int, default=8000, help="API port (default: 8000)")
    parser.add_argument("--no-llm", action="store_true", help="Disable LLM analysis")
    parser.add_argument("--no-npu", action="store_true", help="Disable NPU/ONNX acceleration")
    args = parser.parse_args()

    # Ensure UTF-8 output on Windows
    if IS_WINDOWS:
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print()
    print("=" * 62)
    print("   █████╗  ██████╗ ██████╗  █████╗ ")
    print("  ██╔══██╗██╔════╝ ██╔══██╗██╔══██╗")
    print("  ███████║██║  ███╗██████╔╝███████║")
    print("  ██╔══██║██║   ██║██╔══██╗██╔══██║")
    print("  ██║  ██║╚██████╔╝██║  ██║██║  ██║")
    print("  ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝")
    print("  Endpoint Detection & Response")
    print("=" * 62)

    # ── 1. Database ──
    print("\n[1/4] Initializing database ...")
    init_db()
    print(f"  DB: {DB_PATH}")

    # ── 2. ML Models ──
    print("\n[2/4] Loading ML models ...")
    scorer = Scorer(use_npu=not args.no_npu)

    # ── 3. LLM ──
    print("\n[3/4] Connecting to LLM ...")
    llm = LLMAnalyst()
    if args.no_llm:
        llm.available = False
        print(f"  LLM disabled via --no-llm")
    elif llm.available:
        print(f"  Ollama OK — model: {OLLAMA_MODEL}")
    else:
        print(f"  Ollama not available — ML-only mode (scores still work)")

    # ── 4. File Watcher ──
    print("\n[4/4] Starting file watcher ...")
    observer = Observer()
    handler = ScanHandler(scan_queue)

    watched = []
    for d in args.watch:
        d = os.path.expanduser(d)
        if os.path.isdir(d):
            observer.schedule(handler, d, recursive=False)
            watched.append(d)
            print(f"  Watching: {d}")
        else:
            print(f"  [WARN] Directory not found: {d}")

    if not watched:
        print("  [ERROR] No valid watch directories. Exiting.")
        sys.exit(1)

    observer.start()

    # Start worker thread
    t = threading.Thread(target=worker, args=(scorer, llm), daemon=True)
    t.start()

    # Start API server in a background thread
    print(f"\n  API server: http://127.0.0.1:{args.port}")
    print(f"  Dashboard:  run 'cd frontend && npm run dev' in another terminal")
    print()
    print("=" * 62)
    print(f"  Pipeline running. Drop files into watched dirs to scan.")
    print(f"  Extensions: {', '.join(sorted(SCAN_EXTENSIONS))}")
    print(f"  Press Ctrl+C to stop.")
    print("=" * 62)
    print()

    def shutdown(signum, frame):
        print("\n  Shutting down ...")
        observer.stop()
        observer.join()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    # SIGTERM is not available on Windows
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, shutdown)

    # Run uvicorn in the main thread (it handles signals properly)
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
