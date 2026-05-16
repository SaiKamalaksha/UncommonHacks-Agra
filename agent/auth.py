import os
import sys
import requests

# TEMP: dummy credentials for testing
DUMMY_EMAIL = "test@agra.com"
DUMMY_PASSWORD = "agra1234"
DUMMY_TOKEN = "dummy_token_123"

BACKEND_URL = "http://127.0.0.1:8000"

def get_token_path() -> str:
    # save token next to the .exe, not inside temp bundle
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "auth_token.txt")

def verify_token(id_token: str) -> bool:
    if id_token == DUMMY_TOKEN:
        return True
    try:
        response = requests.post(
            f"{BACKEND_URL}/verify-token",
            json={"token": id_token},
            timeout=5
        )
        return response.status_code == 200
    except Exception as e:
        print(f"[AUTH ERROR] {e}")
        return False

def save_token(token: str):
    path = get_token_path()
    with open(path, "w") as f:
        f.write(token)
    print(f"[AUTH] Token saved to {path}")

def load_token() -> str:
    try:
        path = get_token_path()
        with open(path, "r") as f:
            token = f.read().strip()
            if token:
                print("[AUTH] Token loaded")
                return token
            return None
    except:
        return None

def clear_token():
    try:
        os.remove(get_token_path())
        print("[AUTH] Token cleared")
    except:
        pass