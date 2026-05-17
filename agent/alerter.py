import requests

from agent.config import AgentConfig
from agent.scorer import ScanResult


class Alerter:
    def __init__(self, config: AgentConfig, user_email: str | None = None):
        self.backend_url = config.backend_url
        self.user_email = user_email

    def send_alert(self, result: ScanResult) -> bool:
        payload = {
            "timestamp": result.timestamp,
            "filename": result.filename,
            "filepath": result.filepath,
            "file_hash": result.file_hash_sha256,
            "score": result.threat_score,
            "classification": result.classification,
            "lgbm_score": result.lgbm_score,
            "rf_score": result.rf_score,
            "cluster_id": result.cluster_id,
            "hdbscan_cluster_id": result.hdbscan_cluster_id,
            "llm_analysis": result.llm_analysis,
            "user_email": self.user_email,
        }
        try:
            r = requests.post(
                f"{self.backend_url}/api/alerts", json=payload, timeout=5
            )
            return r.status_code == 200
        except Exception as e:
            print(f"  Failed to send alert: {e}")
            return False
