import sys
import pickle
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")


def check_imports():
    missing = []
    for pkg, imp in [
        ("thrember",      "thrember"),
        ("lightgbm",      "lightgbm"),
        ("scikit-learn",  "sklearn"),
        ("numpy",         "numpy"),
        ("matplotlib",    "matplotlib"),
    ]:
        try:
            __import__(imp)
        except ImportError:
            missing.append(pkg)
    if missing:
        print("\n[ERROR] Missing packages:")
        for p in missing:
            print(f"  pip install {p}")
        sys.exit(1)


def evaluate():
    import numpy as np
    import lightgbm as lgb
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec
    from sklearn.metrics import (
        confusion_matrix, roc_auc_score, accuracy_score,
        precision_score, recall_score, f1_score,
        roc_curve, precision_recall_curve
    )
    import thrember

    model_dir = Path("./model")
    data_dir  = Path("./ember_data")

    print("\nLoading test data...")
    X_test, y_test = thrember.read_vectorized_features(str(data_dir), "test")
    mask = y_test != -1
    X_te, y_te = X_test[mask], y_test[mask]
    print(f"  Test samples : {X_te.shape[0]:,}")

    print("Loading LightGBM model...")
    lgbm = lgb.Booster(model_file=str(model_dir / "lgbm_classifier.model"))
    print("Loading Random Forest model...")
    with open(model_dir / "random_forest_classifier.pkl", "rb") as f:
        rf = pickle.load(f)

    print("Running predictions...")
    lgbm_probs  = lgbm.predict(X_te)
    lgbm_preds  = (lgbm_probs > 0.5).astype(int)
    rf_preds    = rf.predict(X_te)
    rf_probs    = rf.predict_proba(X_te)[:, 1]

    def get_metrics(y_true, y_pred, y_prob):
        return {
            "ROC AUC":   round(roc_auc_score(y_true, y_prob), 4),
            "Accuracy":  round(accuracy_score(y_true, y_pred), 4),
            "Precision": round(precision_score(y_true, y_pred, zero_division=0), 4),
            "Recall":    round(recall_score(y_true, y_pred, zero_division=0), 4),
            "F1":        round(f1_score(y_true, y_pred, zero_division=0), 4),
            "FP Rate":   round((((y_pred == 1) & (y_true == 0)).sum() / (y_true == 0).sum()), 4),
            "FN Rate":   round((((y_pred == 0) & (y_true == 1)).sum() / (y_true == 1).sum()), 4),
        }

    lgbm_metrics = get_metrics(y_te, lgbm_preds, lgbm_probs)
    rf_metrics   = get_metrics(y_te, rf_preds,   rf_probs)

    print("\n  LightGBM:")
    for k, v in lgbm_metrics.items():
        print(f"    {k:<12}: {v}")
    print("\n  Random Forest:")
    for k, v in rf_metrics.items():
        print(f"    {k:<12}: {v}")

    fig = plt.figure(figsize=(16, 12))
    fig.suptitle("EMBER2024 Model Evaluation", fontsize=16, fontweight="bold", y=0.98)
    gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.4, wspace=0.35)

    cmap = plt.cm.Blues

    def plot_cm(ax, y_true, y_pred, title):
        cm = confusion_matrix(y_true, y_pred)
        im = ax.imshow(cm, interpolation="nearest", cmap=cmap)
        ax.set_title(title, fontweight="bold", pad=10)
        ax.set_xlabel("Predicted label")
        ax.set_ylabel("True label")
        ax.set_xticks([0, 1])
        ax.set_yticks([0, 1])
        ax.set_xticklabels(["Benign", "Malicious"])
        ax.set_yticklabels(["Benign", "Malicious"])
        thresh = cm.max() / 2
        for i in range(2):
            for j in range(2):
                ax.text(j, i, f"{cm[i,j]:,}", ha="center", va="center",
                        color="white" if cm[i,j] > thresh else "black", fontsize=12)
        labels = [["TN", "FP"], ["FN", "TP"]]
        for i in range(2):
            for j in range(2):
                ax.text(j, i + 0.3, labels[i][j], ha="center", va="center",
                        color="white" if cm[i,j] > thresh else "gray", fontsize=9)
        plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    ax1 = fig.add_subplot(gs[0, 0])
    plot_cm(ax1, y_te, lgbm_preds, "LightGBM — Confusion Matrix")

    ax2 = fig.add_subplot(gs[0, 1])
    plot_cm(ax2, y_te, rf_preds, "Random Forest — Confusion Matrix")

    ax3 = fig.add_subplot(gs[0, 2])
    metrics_names = list(lgbm_metrics.keys())
    x = np.arange(len(metrics_names))
    width = 0.35
    bars1 = ax3.bar(x - width/2, list(lgbm_metrics.values()), width, label="LightGBM", color="#2196F3", alpha=0.85)
    bars2 = ax3.bar(x + width/2, list(rf_metrics.values()),   width, label="Random Forest", color="#FF9800", alpha=0.85)
    ax3.set_title("Metrics Comparison", fontweight="bold", pad=10)
    ax3.set_xticks(x)
    ax3.set_xticklabels(metrics_names, rotation=30, ha="right", fontsize=9)
    ax3.set_ylim(0, 1.1)
    ax3.legend()
    ax3.grid(axis="y", alpha=0.3)
    for bar in bars1:
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                 f"{bar.get_height():.3f}", ha="center", va="bottom", fontsize=7, rotation=45)
    for bar in bars2:
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                 f"{bar.get_height():.3f}", ha="center", va="bottom", fontsize=7, rotation=45)

    ax4 = fig.add_subplot(gs[1, 0:2])
    fpr_lgbm, tpr_lgbm, _ = roc_curve(y_te, lgbm_probs)
    fpr_rf,   tpr_rf,   _ = roc_curve(y_te, rf_probs)
    ax4.plot(fpr_lgbm, tpr_lgbm, color="#2196F3", lw=2,
             label=f"LightGBM (AUC = {lgbm_metrics['ROC AUC']})")
    ax4.plot(fpr_rf,   tpr_rf,   color="#FF9800", lw=2,
             label=f"Random Forest (AUC = {rf_metrics['ROC AUC']})")
    ax4.plot([0, 1], [0, 1], "k--", lw=1, alpha=0.4, label="Random classifier")
    ax4.set_xlabel("False Positive Rate")
    ax4.set_ylabel("True Positive Rate")
    ax4.set_title("ROC Curve", fontweight="bold", pad=10)
    ax4.legend(loc="lower right")
    ax4.grid(alpha=0.3)

    ax5 = fig.add_subplot(gs[1, 2])
    categories = ["Benign (0)", "Malicious (1)"]
    counts = [int((y_te == 0).sum()), int((y_te == 1).sum())]
    colors = ["#4CAF50", "#F44336"]
    bars = ax5.bar(categories, counts, color=colors, alpha=0.85, edgecolor="white")
    ax5.set_title("Test Set Class Balance", fontweight="bold", pad=10)
    ax5.set_ylabel("Sample count")
    ax5.grid(axis="y", alpha=0.3)
    for bar, count in zip(bars, counts):
        ax5.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(counts)*0.01,
                 f"{count:,}", ha="center", va="bottom", fontweight="bold")

    out_path = model_dir / "evaluation.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"\n  Saved visualization -> {out_path}")
    plt.show()
    print("\nDone!")


if __name__ == "__main__":
    check_imports()
    evaluate()