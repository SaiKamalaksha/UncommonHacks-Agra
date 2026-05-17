from typing import Optional
from pydantic import BaseModel

class AlertIn(BaseModel):
    timestamp: str
    filename: str
    filepath: str
    file_hash: str
    score: int
    classification: str
    lgbm_score: float
    rf_score: float
    cluster_id: int
    hdbscan_cluster_id: int = -1
    llm_analysis: Optional[str] = None
    user_email: Optional[str] = None

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
    user_email: Optional[str] = None
    verdict: str

class StatsOut(BaseModel):
    total_scanned: int
    threats: int
    warnings: int
    safe: int

class UserRegister(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class TokenOut(BaseModel):
    token: str
    email: str