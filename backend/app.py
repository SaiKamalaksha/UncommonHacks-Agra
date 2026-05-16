from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend import database
from backend.models import AlertIn, AlertOut, StatsOut


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()
    yield


app = FastAPI(title="AGRA EDR Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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
