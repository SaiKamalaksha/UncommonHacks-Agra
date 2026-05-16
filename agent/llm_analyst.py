import requests

from agent.scorer import ScanResult


class LLMAnalyst:
    def __init__(self, model: str = "qwen2.5:0.5b", base_url: str = "http://127.0.0.1:11434"):
        self.model = model
        self.base_url = base_url
        self.available = self._check_availability()

    def _check_availability(self) -> bool:
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return r.status_code == 200
        except Exception:
            return False

    def analyze(self, result: ScanResult) -> str | None:
        if not self.available:
            self.available = self._check_availability()
            if not self.available:
                return None

        prompt = self._build_prompt(result)
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": 256},
                },
                timeout=30,
            )
            response.raise_for_status()
            return response.json().get("response", "").strip()
        except Exception as e:
            print(f"  LLM analysis failed: {e}")
            return None

    def _build_prompt(self, result: ScanResult) -> str:
        return (
            "You are a cybersecurity analyst for an EDR system. "
            "Analyze this file scan result and provide a brief threat assessment.\n\n"
            f"FILE: {result.filename}\n"
            f"SIZE: {result.file_size} bytes\n"
            f"SHA256: {result.file_hash_sha256}\n\n"
            "ML ANALYSIS:\n"
            f"- LightGBM malware probability: {result.lgbm_score:.1%}\n"
            f"- Random Forest malware probability: {result.rf_score:.1%}\n"
            f"- Combined threat score: {result.threat_score}/100\n"
            f"- Classification: {result.classification}\n"
            f"- KMeans cluster ID: {result.cluster_id}\n"
            f"- HDBSCAN cluster: {result.hdbscan_cluster_id} (-1 means anomalous/unclustered)\n\n"
            "Provide a 2-3 sentence threat finding. Include: what type of threat this likely is, "
            "confidence level, and recommended action. Be concise."
        )
