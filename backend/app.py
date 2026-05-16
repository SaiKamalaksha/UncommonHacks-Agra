import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from contextlib import asynccontextmanager
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
import database
import models
from models import AlertIn, AlertOut, StatsOut, UserRegister, UserLogin, TokenOut

SECRET_KEY = os.environ.get("SECRET_KEY", "agra_secret_hackathon_key")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 72

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)

def create_token(email: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)
    return jwt.encode(
        {"sub": email, "exp": expire},
        SECRET_KEY,
        algorithm=ALGORITHM
    )

def decode_token(token: str) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except:
        return None

@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()
    existing = database.get_user("test@agra.com")
    if not existing:
        database.create_user("test@agra.com", hash_password("agra1234"))
        print("[STARTUP] Default test user created")
    yield

app = FastAPI(title="AGRA EDR Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── auth ─────────────────────────────────────────────────────────────
@app.post("/login", response_model=TokenOut)
def login(body: UserLogin):
    user = database.get_user(body.email)
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(body.email)
    return {"token": token, "email": body.email}

@app.post("/register", response_model=TokenOut)
def register(body: UserRegister):
    user_id = database.create_user(body.email, hash_password(body.password))
    if not user_id:
        raise HTTPException(status_code=400, detail="Email already registered")
    token = create_token(body.email)
    return {"token": token, "email": body.email}

@app.post("/verify-token")
def verify_token(body: dict):
    token = body.get("token")
    email = decode_token(token)
    if not email:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"email": email, "valid": True}

# ── alerts ────────────────────────────────────────────────────────────
@app.get("/api/alerts", response_model=List[AlertOut])
def get_alerts(limit: int = 50):
    return database.get_recent_alerts(limit)

@app.post("/api/alerts")
def create_alert(alert: AlertIn):
    alert_id = database.insert_alert(alert.model_dump())
    return {"id": alert_id, "status": "ok"}

@app.get("/api/stats", response_model=StatsOut)
def get_stats():
    return database.get_stats()