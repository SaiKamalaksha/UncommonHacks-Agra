from __future__ import annotations
from pathlib import Path
from typing import Optional, Tuple
import numpy as np

SessionPair = Tuple[Optional[object], Optional[object], str]

def _provider_chain():
    import onnxruntime as ort
    available = set(ort.get_available_providers())
    chain = []
    if "DmlExecutionProvider" in available:
        chain.append((
            ["DmlExecutionProvider", "CPUExecutionProvider"],
            "Intel NPU via DirectML"
        ))
    chain.append((["CPUExecutionProvider"], "ONNX CPU"))
    return chain

def load_classifier_sessions(model_dir: Path) -> SessionPair:
    lgbm_path = model_dir / "lgbm_classifier.onnx"
    rf_path = model_dir / "random_forest_classifier.onnx"

    if not lgbm_path.exists() or not rf_path.exists():
        return None, None, "native"

    try:
        import onnxruntime as ort
    except ImportError:
        return None, None, "native"

    opts = ort.SessionOptions()
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

    for providers, label in _provider_chain():
        try:
            lgbm = ort.InferenceSession(str(lgbm_path), sess_options=opts, providers=providers)
            rf = ort.InferenceSession(str(rf_path), sess_options=opts, providers=providers)
            active = lgbm.get_providers()
            if "DmlExecutionProvider" in active:
                mode = label
            else:
                mode = "ONNX CPU"
            return lgbm, rf, mode
        except Exception:
            continue

    return None, None, "native"

def onnx_classify(lgbm_sess, rf_sess, features: np.ndarray) -> Tuple[float, float]:
    x = features.astype(np.float32)
    lgbm_out = lgbm_sess.run(None, {"input": x})
    lgbm_prob = float(lgbm_out[1][0][1])
    rf_out = rf_sess.run(None, {"input": x})
    rf_prob = float(rf_out[1][0][1])
    return lgbm_prob, rf_prob