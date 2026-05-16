#!/usr/bin/env python3
"""
Convert trained LightGBM and Random Forest models to ONNX format
for accelerated inference via ONNX Runtime (with OpenVINO execution provider).

Usage:
    python model/convert_onnx.py

Outputs:
    model/lgbm_classifier.onnx
    model/random_forest_classifier.onnx
"""

import pickle
from pathlib import Path

import lightgbm as lgb
import numpy as np
import onnx
import onnxmltools
from onnxmltools.convert.common.data_types import FloatTensorType as OnnxmlFloatTensorType
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType as SklFloatTensorType

MODEL_DIR = Path(__file__).resolve().parent
NUM_FEATURES = 2568


def convert_lgbm():
    print("Converting LightGBM ...")
    model = lgb.Booster(model_file=str(MODEL_DIR / "lgbm_classifier.model"))

    onnx_model = onnxmltools.convert_lightgbm(
        model,
        initial_types=[("input", OnnxmlFloatTensorType([None, NUM_FEATURES]))],
        target_opset=12,
    )

    onnx_path = MODEL_DIR / "lgbm_classifier.onnx"
    onnxmltools.utils.save_model(onnx_model, str(onnx_path))
    print(f"  Saved: {onnx_path} ({onnx_path.stat().st_size / 1024:.0f} KB)")


def convert_rf():
    print("Converting Random Forest ...")
    with open(MODEL_DIR / "random_forest_classifier.pkl", "rb") as f:
        rf = pickle.load(f)

    onnx_model = convert_sklearn(
        rf,
        initial_types=[("input", SklFloatTensorType([None, NUM_FEATURES]))],
        target_opset=12,
    )

    onnx_path = MODEL_DIR / "random_forest_classifier.onnx"
    onnx.save_model(onnx_model, str(onnx_path))
    print(f"  Saved: {onnx_path} ({onnx_path.stat().st_size / 1024:.0f} KB)")


def verify():
    print("\nVerifying ONNX models ...")
    import onnxruntime as ort

    dummy = np.zeros((1, NUM_FEATURES), dtype=np.float32)

    for name in ["lgbm_classifier.onnx", "random_forest_classifier.onnx"]:
        sess = ort.InferenceSession(
            str(MODEL_DIR / name),
            providers=["CPUExecutionProvider"],
        )
        out = sess.run(None, {"input": dummy})
        print(f"  {name}: outputs={len(out)} — OK")

    print("\nDone! ONNX models ready for NPU acceleration.")


if __name__ == "__main__":
    convert_lgbm()
    convert_rf()
    verify()
