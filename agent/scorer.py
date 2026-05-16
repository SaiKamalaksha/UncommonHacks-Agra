import hashlib
import pickle
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import lightgbm as lgb
import numpy as np


@dataclass
class ScanResult:
    filepath: str
    filename: str
    file_size: int
    file_hash_sha256: str
    lgbm_score: float
    rf_score: float
    threat_score: int
    classification: str
    cluster_id: int
    hdbscan_cluster_id: int
    top_features: List[dict] = field(default_factory=list)
    llm_analysis: Optional[str] = None
    timestamp: str = ""


class Scorer:
    def __init__(self, model_dir: str):
        model_path = Path(model_dir)
        print(f"  Loading models from {model_path} ...")

        self.lgbm = lgb.Booster(model_file=str(model_path / "lgbm_classifier.model"))

        with open(model_path / "random_forest_classifier.pkl", "rb") as f:
            self.rf = pickle.load(f)

        with open(model_path / "kmeans_clusterer.pkl", "rb") as f:
            self.kmeans = pickle.load(f)

        with open(model_path / "hdbscan_clusterer.pkl", "rb") as f:
            self.hdbscan_model = pickle.load(f)

        with open(model_path / "cluster_scaler.pkl", "rb") as f:
            self.scaler = pickle.load(f)

        with open(model_path / "cluster_pca.pkl", "rb") as f:
            self.pca = pickle.load(f)

        self._feature_importance = self.lgbm.feature_importance(importance_type="gain")
        print("  All models loaded.")

    def _file_hash(self, filepath: str) -> str:
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def extract_features(self, filepath: str) -> np.ndarray:
        """Extract 702-dim feature vector from a binary using thrember.

        thrember's batch API (create_vectorized_features) works on directories.
        For single-file inference we write to a temp dir, vectorize, and read back.
        """
        import shutil
        import tempfile

        import thrember

        tmp_dir = tempfile.mkdtemp(prefix="agra_scan_")
        try:
            shutil.copy2(filepath, tmp_dir)
            thrember.create_vectorized_features(tmp_dir, label_type="label")
            X, _ = thrember.read_vectorized_features(tmp_dir, "train")
            return X[:1]
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def score_file(self, filepath: str) -> ScanResult:
        features = self.extract_features(filepath)

        # --- Classification ---
        lgbm_prob = float(self.lgbm.predict(features)[0])
        rf_prob = float(self.rf.predict_proba(features)[0][1])

        blended = 0.7 * lgbm_prob + 0.3 * rf_prob
        threat_score = int(blended * 100)

        if threat_score > 70:
            classification = "malicious"
        elif threat_score >= 40:
            classification = "suspicious"
        else:
            classification = "benign"

        # --- Clustering ---
        scaled = self.scaler.transform(features)
        reduced = self.pca.transform(scaled)
        km_cluster = int(self.kmeans.predict(reduced)[0])

        try:
            import hdbscan
            hdb_labels, _ = hdbscan.approximate_predict(self.hdbscan_model, reduced)
            hdb_cluster = int(hdb_labels[0])
        except Exception:
            hdb_cluster = -1

        # --- Top contributing features ---
        importance = self._feature_importance
        feat_vals = features[0]
        weighted = np.abs(feat_vals) * importance
        top_idx = np.argsort(weighted)[-5:][::-1]
        top_features = [
            {"index": int(i), "value": float(feat_vals[i]), "importance": float(importance[i])}
            for i in top_idx
        ]

        return ScanResult(
            filepath=filepath,
            filename=Path(filepath).name,
            file_size=Path(filepath).stat().st_size,
            file_hash_sha256=self._file_hash(filepath),
            lgbm_score=lgbm_prob,
            rf_score=rf_prob,
            threat_score=threat_score,
            classification=classification,
            cluster_id=km_cluster,
            hdbscan_cluster_id=hdb_cluster,
            top_features=top_features,
            timestamp=datetime.now().strftime("%H:%M:%S"),
        )
