import onnxruntime as ort
from pathlib import Path
import numpy as np

print("Available providers:")
for p in ort.get_available_providers():
    print(f"  {p}")

print("\nTrying DirectML NPU session...")
MODEL_DIR = Path(__file__).resolve().parent
lgbm_path = MODEL_DIR / "lgbm_classifier.onnx"
rf_path = MODEL_DIR / "random_forest_classifier.onnx"

if not lgbm_path.exists():
    print("  lgbm_classifier.onnx not found — run convert_onnx.py first")
elif not rf_path.exists():
    print("  random_forest_classifier.onnx not found — run convert_onnx.py first")
else:
    try:
        # test lgbm
        print("\n  Loading LightGBM ONNX session...")
        lgbm_sess = ort.InferenceSession(
            str(lgbm_path),
            providers=["DmlExecutionProvider", "CPUExecutionProvider"]
        )
        active = lgbm_sess.get_providers()
        print(f"  Active providers: {active}")
        if "DmlExecutionProvider" in active:
            print("  ✅ DirectML IS ACTIVE — running on NPU/GPU")
        else:
            print("  ⚠️ Fell back to CPU")

        # test rf
        print("\n  Loading Random Forest ONNX session...")
        rf_sess = ort.InferenceSession(
            str(rf_path),
            providers=["DmlExecutionProvider", "CPUExecutionProvider"]
        )
        active_rf = rf_sess.get_providers()
        print(f"  Active providers: {active_rf}")
        if "DmlExecutionProvider" in active_rf:
            print("  ✅ Random Forest on DirectML")
        else:
            print("  ⚠️ Random Forest fell back to CPU")

        # run inference test on both
        print("\n  Running inference test...")
        dummy = np.zeros((1, 2568), dtype=np.float32)

        lgbm_out = lgbm_sess.run(None, {"input": dummy})
        print(f"  LightGBM output tensors: {len(lgbm_out)}")
        print(f"  LightGBM prob: {lgbm_out[1][0][1]:.4f}")

        rf_out = rf_sess.run(None, {"input": dummy})
        print(f"  Random Forest output tensors: {len(rf_out)}")
        print(f"  Random Forest prob: {rf_out[1][0][1]:.4f}")

        print("\n  ✅ Both models running — NPU verification complete")

    except Exception as e:
        print(f"\n  Error: {e}")
        import traceback
        traceback.print_exc()