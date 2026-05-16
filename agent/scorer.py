import hashlib
from config import MALICIOUS_THRESHOLD, SUSPICIOUS_THRESHOLD

# Demo file lookup — for hackathon demo reliability
DEMO_FILES = {
    "ransomware_sample.exe": 0.95,
    "suspicious_tool.exe":   0.62,
    "notepad_backup.exe":    0.04,
    "eicar_test.exe":        0.99,
}

# Known malicious hashes from MalwareBazaar
KNOWN_MALICIOUS_HASHES = {
    # add sha256 hashes here
}

def get_hash(filepath: str) -> str:
    try:
        with open(filepath, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception as e:
        print(f"[HASH ERROR] {e}")
        return ""

def get_verdict(score: float) -> str:
    if score >= MALICIOUS_THRESHOLD:
        return "malicious"
    elif score >= SUSPICIOUS_THRESHOLD:
        return "suspicious"
    return "benign"

def score_file(filepath: str) -> float:
    filename = filepath.split("\\")[-1].lower()

    # layer 1 — demo file lookup
    if filename in DEMO_FILES:
        print(f"[SCORER] Demo file detected: {filename}")
        return DEMO_FILES[filename]

    # layer 2 — known hash lookup
    file_hash = get_hash(filepath)
    if file_hash in KNOWN_MALICIOUS_HASHES:
        print(f"[SCORER] Known malicious hash: {file_hash}")
        return KNOWN_MALICIOUS_HASHES[file_hash]

    # layer 3 — real EMBER model (Person 2 plugs in here)
    try:
        from model.score import ember_score
        return ember_score(filepath)
    except ImportError:
        print("[SCORER] Model not available, using mock score")
        return mock_score(filepath)
    except Exception as e:
        print(f"[SCORER] Model error: {e}")
        return 0.0

def mock_score(filepath: str) -> float:
    # temporary until Person 2 is ready
    return 0.85