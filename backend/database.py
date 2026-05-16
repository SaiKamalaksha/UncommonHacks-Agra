import sqlite3
import threading
from pathlib import Path

DB_PATH = Path(__file__).parent / "agra.db"
_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    if not hasattr(_local, "conn"):
        _local.conn = sqlite3.connect(str(DB_PATH))
        _local.conn.row_factory = sqlite3.Row
    return _local.conn


def init_db():
    conn = _get_conn()
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
            cluster_id INTEGER,
            hdbscan_cluster_id INTEGER DEFAULT -1,
            llm_analysis TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()


def insert_alert(alert: dict) -> int:
    conn = _get_conn()
    cur = conn.execute(
        """INSERT INTO alerts
           (timestamp, filename, filepath, file_hash, score, classification,
            lgbm_score, rf_score, cluster_id, hdbscan_cluster_id, llm_analysis)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            alert["timestamp"],
            alert["filename"],
            alert["filepath"],
            alert["file_hash"],
            alert["score"],
            alert["classification"],
            alert["lgbm_score"],
            alert["rf_score"],
            alert["cluster_id"],
            alert.get("hdbscan_cluster_id", -1),
            alert.get("llm_analysis"),
        ),
    )
    conn.commit()
    return cur.lastrowid


def get_recent_alerts(limit: int = 50) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM alerts ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()

    results = []
    for row in rows:
        d = dict(row)
        score = d["score"]
        if score > 70:
            d["verdict"] = "Malicious"
        elif score >= 40:
            d["verdict"] = "Suspicious"
        else:
            d["verdict"] = "Benign"
        results.append(d)
    return results


def get_stats() -> dict:
    conn = _get_conn()
    row = conn.execute(
        """SELECT
             COUNT(*) as total_scanned,
             SUM(CASE WHEN score > 70 THEN 1 ELSE 0 END) as threats,
             SUM(CASE WHEN score >= 40 AND score <= 70 THEN 1 ELSE 0 END) as warnings,
             SUM(CASE WHEN score < 40 THEN 1 ELSE 0 END) as safe
           FROM alerts"""
    ).fetchone()
    return dict(row)

def init_db():
    conn = _get_conn()
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
            cluster_id INTEGER,
            hdbscan_cluster_id INTEGER DEFAULT -1,
            llm_analysis TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

def create_user(email: str, password_hash: str) -> int:
    conn = _get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            (email, password_hash)
        )
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        return None

def get_user(email: str) -> dict:
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM users WHERE email = ?", (email,)
    ).fetchone()
    return dict(row) if row else None