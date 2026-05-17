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
            user_email TEXT,
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

    # Migrate existing alerts table if this schema was created earlier.
    columns = [col[1] for col in conn.execute("PRAGMA table_info(alerts)").fetchall()]
    if "user_email" not in columns:
        conn.execute("ALTER TABLE alerts ADD COLUMN user_email TEXT")
        conn.commit()
    if "created_by" in columns:
        conn.execute(
            "UPDATE alerts SET user_email = created_by WHERE user_email IS NULL AND created_by IS NOT NULL"
        )
        conn.commit()


def insert_alert(alert: dict) -> int:
    conn = _get_conn()
    cur = conn.execute(
        """INSERT INTO alerts
           (timestamp, filename, filepath, file_hash, score, classification,
            lgbm_score, rf_score, cluster_id, hdbscan_cluster_id, llm_analysis, user_email)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
            alert.get("user_email"),
        ),
    )
    conn.commit()
    return cur.lastrowid


def get_recent_alerts(limit: int = 50, user_email: str | None = None) -> list[dict]:
    conn = _get_conn()
    if user_email:
        rows = conn.execute(
            "SELECT * FROM alerts WHERE user_email = ? ORDER BY id DESC LIMIT ?",
            (user_email, limit),
        ).fetchall()
    else:
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


def get_stats(user_email: str | None = None) -> dict:
    conn = _get_conn()
    if user_email:
        query = """SELECT
             COUNT(*) as total_scanned,
             SUM(CASE WHEN score > 70 THEN 1 ELSE 0 END) as threats,
             SUM(CASE WHEN score >= 40 AND score <= 70 THEN 1 ELSE 0 END) as warnings,
             SUM(CASE WHEN score < 40 THEN 1 ELSE 0 END) as safe
           FROM alerts WHERE user_email = ?"""
        row = conn.execute(query, (user_email,)).fetchone()
    else:
        row = conn.execute(
            """SELECT
                 COUNT(*) as total_scanned,
                 SUM(CASE WHEN score > 70 THEN 1 ELSE 0 END) as threats,
                 SUM(CASE WHEN score >= 40 AND score <= 70 THEN 1 ELSE 0 END) as warnings,
                 SUM(CASE WHEN score < 40 THEN 1 ELSE 0 END) as safe
               FROM alerts"""
        ).fetchone()

    if row is None:
        return {"total_scanned": 0, "threats": 0, "warnings": 0, "safe": 0}
    return {
        "total_scanned": row["total_scanned"] or 0,
        "threats": row["threats"] or 0,
        "warnings": row["warnings"] or 0,
        "safe": row["safe"] or 0,
    }

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