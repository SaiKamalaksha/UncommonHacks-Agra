import hashlib
import pickle
import shutil
import tempfile
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import lightgbm as lgb
import numpy as np

try:
    import hdbscan as _hdbscan_module
    _HDBSCAN_AVAILABLE = True
except ImportError:
    _HDBSCAN_AVAILABLE = False

EICAR_SIGNATURE = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
AGRA_TEST_SIGNATURE = b"AGRA-EDR-TEST-MALWARE"
_SIG_READ_LIMIT = 1024 * 1024  # 1 MB


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


class EncryptedArchiveDetected(Exception):
    pass


class Scorer:
    def __init__(self, model_dir: str, use_npu: bool = True):
        model_path = Path(model_dir)
        print(f"  Loading models from {model_path} ...")

        self._onnx_lgbm = None
        self._onnx_rf = None
        self._onnx_classify = None
        self._onnx_active = False
        self.rf = None

        if use_npu:
            try:
                import importlib.util

                spec = importlib.util.spec_from_file_location(
                    "onnx_sessions", model_path / "onnx_sessions.py"
                )
                onnx_mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(onnx_mod)
                self._onnx_lgbm, self._onnx_rf, mode = onnx_mod.load_classifier_sessions(model_path)
                if self._onnx_lgbm is not None:
                    self._onnx_classify = onnx_mod.onnx_classify
                    self._onnx_active = True
                    print(f"  ONNX Runtime loaded — mode: {mode}")
            except Exception:
                pass

        self.lgbm = lgb.Booster(model_file=str(model_path / "lgbm_classifier.model"))

        if not self._onnx_active:
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

    def _hash_and_check_raw(self, filepath: str) -> Tuple[str, Optional[str]]:
        """Single streaming pass: compute SHA-256 and check the first 1 MB for test signatures."""
        h = hashlib.sha256()
        header = bytearray()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
                if len(header) < _SIG_READ_LIMIT:
                    header += chunk[: _SIG_READ_LIMIT - len(header)]
        sig: Optional[str] = None
        if EICAR_SIGNATURE in header:
            sig = "EICAR test signature"
        elif AGRA_TEST_SIGNATURE in header:
            sig = "AGRA test signature"
        return h.hexdigest(), sig

    def _detect_test_signature_zip(self, filepath: str) -> Optional[str]:
        """Check for test signatures inside a ZIP. Raises EncryptedArchiveDetected if password-protected."""
        with zipfile.ZipFile(filepath) as archive:
            for name in archive.namelist():
                try:
                    with archive.open(name) as member:
                        data = member.read(_SIG_READ_LIMIT)
                        if EICAR_SIGNATURE in data:
                            return "EICAR test signature"
                        if AGRA_TEST_SIGNATURE in data:
                            return "AGRA test signature"
                except RuntimeError as e:
                    if "encrypted" in str(e).lower() or "password" in str(e).lower():
                        raise EncryptedArchiveDetected(str(e)) from e
                    raise
        return None

    def _manual_result(
        self,
        filepath: str,
        file_size: int,
        file_hash: str,
        score: int,
        classification: str,
        reason: str,
    ) -> ScanResult:
        path = Path(filepath)
        return ScanResult(
            filepath=filepath,
            filename=path.name,
            file_size=file_size,
            file_hash_sha256=file_hash,
            lgbm_score=score / 100,
            rf_score=score / 100,
            threat_score=score,
            classification=classification,
            cluster_id=-1,
            hdbscan_cluster_id=-1,
            top_features=[{"name": reason, "value": 1.0, "importance": 1.0}],
            llm_analysis=reason,
            timestamp=datetime.now().strftime("%H:%M:%S"),
        )

    def _test_signature_result(
        self, filepath: str, file_size: int, file_hash: str, signature_name: str
    ) -> ScanResult:
        return self._manual_result(
            filepath,
            file_size,
            file_hash,
            100,
            "malicious",
            f"{signature_name} detected. This is a harmless validation sample.",
        )

    def extract_features(self, filepath: str) -> np.ndarray:
        """Extract 702-dim feature vector from a binary using thrember.

        thrember's batch API (create_vectorized_features) works on directories.
        For single-file inference we write to a temp dir, vectorize, and read back.
        """
        import thrember  # kept here: may be absent in packaged runtime

        tmp_dir = tempfile.mkdtemp(prefix="agra_scan_")
        try:
            shutil.copy2(filepath, tmp_dir)
            thrember.create_vectorized_features(tmp_dir, label_type="label")
            X, _ = thrember.read_vectorized_features(tmp_dir, "train")
            return X[:1]
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def score_file(self, filepath: str) -> ScanResult:
        path = Path(filepath)

        # Capture metadata before any processing so we have it even if the file
        # is deleted mid-scan by another process (or by a previous threat-response).
        try:
            file_size = path.stat().st_size
        except OSError:
            file_size = 0

        # Hash + signature detection. For non-zip files this is a single streaming
        # pass; for zip files we need a separate open to walk archive members.
        file_hash = ""
        signature_name: Optional[str] = None
        try:
            if zipfile.is_zipfile(filepath):
                file_hash = self._file_hash(filepath)
                try:
                    signature_name = self._detect_test_signature_zip(filepath)
                except EncryptedArchiveDetected as e:
                    print(f"  [ARCHIVE] Encrypted/password-protected ZIP detected: {e}")
                    return self._manual_result(
                        filepath,
                        file_size,
                        file_hash,
                        100,
                        "malicious",
                        "Encrypted/password-protected archive blocked because contents cannot be inspected.",
                    )
            else:
                file_hash, signature_name = self._hash_and_check_raw(filepath)
        except Exception as e:
            print(f"  [WARN] Pre-scan check failed for {path.name}: {e}")

        if signature_name:
            print(f"  [TEST] {signature_name} detected.")
            return self._test_signature_result(filepath, file_size, file_hash, signature_name)

        try:
            features = self.extract_features(filepath)
        except FileNotFoundError as e:
            print(f"  [WARN] Feature extractor dependency missing: {e}")
            return self._manual_result(
                filepath,
                file_size,
                file_hash,
                80,
                "malicious",
                "Feature extractor failed in packaged runtime; file blocked as a precaution.",
            )

        # --- Classification ---
        if self._onnx_active:
            lgbm_prob, rf_prob = self._onnx_classify(
                self._onnx_lgbm, self._onnx_rf, features
            )
        else:
            lgbm_prob = float(self.lgbm.predict(features)[0])
            rf_prob = float(self.rf.predict_proba(features)[0][1])

        blended = 0.7 * lgbm_prob + 0.3 * rf_prob
        threat_score = int(blended * 100)

        if threat_score >= 70:
            classification = "malicious"
        elif threat_score >= 40:
            classification = "suspicious"
        else:
            classification = "benign"

        # --- Clustering ---
        scaled = self.scaler.transform(features)
        reduced = self.pca.transform(scaled)
        km_cluster = int(self.kmeans.predict(reduced)[0])

        hdb_cluster = -1
        if _HDBSCAN_AVAILABLE:
            try:
                hdb_labels, _ = _hdbscan_module.approximate_predict(self.hdbscan_model, reduced)
                hdb_cluster = int(hdb_labels[0])
            except Exception:
                pass

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
            filename=path.name,
            file_size=file_size,
            file_hash_sha256=file_hash,
            lgbm_score=lgbm_prob,
            rf_score=rf_prob,
            threat_score=threat_score,
            classification=classification,
            cluster_id=km_cluster,
            hdbscan_cluster_id=hdb_cluster,
            top_features=top_features,
            timestamp=datetime.now().strftime("%H:%M:%S"),
        )
