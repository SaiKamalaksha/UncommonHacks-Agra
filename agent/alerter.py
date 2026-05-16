import requests
from config import BACKEND_URL

def send_alert(alert: dict):
    try:
        response = requests.post(
            f"{BACKEND_URL}/alert",
            json=alert,
            timeout=5
        )
        if response.status_code == 200:
            print(f"[ALERT SENT] {alert['filename']} → {alert['verdict']} ({alert['threat_score']:.2f})")
        else:
            print(f"[ALERT FAILED] Status {response.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"[ALERT FAILED] Backend unreachable, storing locally")
        store_locally(alert)
    except Exception as e:
        print(f"[ALERT ERROR] {e}")

def store_locally(alert: dict):
    # fallback if backend is down, write to local log
    with open("local_alerts.log", "a") as f:
        f.write(str(alert) + "\n")