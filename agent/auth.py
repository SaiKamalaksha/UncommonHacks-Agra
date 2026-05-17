import os
import sys
import requests
from jose import jwt

# TEMP: dummy credentials for testing
DUMMY_EMAIL = "test@agra.com"
DUMMY_PASSWORD = "agra1234"
DUMMY_TOKEN = "dummy_token_123"

BACKEND_URL = "https://uncommonhacks-agra-production.up.railway.app"
SECRET_KEY = "agra_secret_hackathon_key"
ALGORITHM = "HS256"


def get_token_path() -> str:
    # save token next to the .exe, not inside temp bundle
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "auth_token.txt")

def decode_token(id_token: str) -> str | None:
    if id_token == DUMMY_TOKEN:
        return DUMMY_EMAIL
    try:
        payload = jwt.decode(id_token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except Exception:
        return None


def verify_token(id_token: str) -> bool:
    if id_token == DUMMY_TOKEN:
        return True
    return decode_token(id_token) is not None


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