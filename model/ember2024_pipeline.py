import os
import sys
import pickle
import argparse
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")


def banner(title: str) -> None:
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def check_imports() -> None:
    missing = []
    for pkg, imp in [
        ("thrember",     "thrember"),
        ("lightgbm",     "lightgbm"),
        ("scikit-learn", "sklearn"),
        ("numpy",        "numpy"),
        ("hdbscan",      "hdbscan"),
        ("tqdm",         "tqdm"),
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


def download_data(data_dir: Path, file_type: str, split: str) -> None:
    import thrember
    banner(f"Downloading EMBER2024 ({file_type}, {split})")
    data_dir.mkdir(parents=True, exist_ok=True)
    thrember.download_dataset(str(data_dir), split=split, file_type=file_type)
    print("  Download complete.")


def vectorize_data(data_dir: Path, label_type: str) -> None:
    import thrember
    banner(f"Vectorizing features (label_type='{label_type}')")
    thrember.create_vectorized_features(str(data_dir), label_type=label_type)
    print("  Vectorization complete.")


def subsample_by_gb(X, y, max_gb: float):
    import numpy as np
    bytes_per_row = X.dtype.itemsize * X.shape[1]
    max_rows = int((max_gb * 1024 ** 3) / bytes_per_row)
    if X.shape[0] <= max_rows:
        print(f"  Data is {X.nbytes / 1024**3:.2f} GB — using all {X.shape[0]:,} rows.")
        return X, y
    idx = np.random.choice(X.shape[0], max_rows, replace=False)
    print(f"  Limiting to {max_gb} GB — using {max_rows:,} of {X.shape[0]:,} rows.")
    return X[idx], y[idx]


def train_clustering(X_train, output_dir: Path) -> dict:
    import numpy as np
    from sklearn.cluster import MiniBatchKMeans
    from sklearn.preprocessing import StandardScaler
    from sklearn.decomposition import PCA
    from sklearn.metrics import silhouette_score, davies_bouldin_score
    import hdbscan

    banner("Clustering (unsupervised)")

    MAX_ROWS = 50_000
    if X_train.shape[0] > MAX_ROWS:
        idx = np.random.choice(X_train.shape[0], MAX_ROWS, replace=False)
        X_c = X_train[idx]
    else:
        X_c = X_train

    print("  Standardizing features...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_c)

    print("  PCA reduction to 50 components...")
    pca = PCA(n_components=min(50, X_scaled.shape[1]), random_state=42)
    X_reduced = pca.fit_transform(X_scaled)
    print(f"  Explained variance: {pca.explained_variance_ratio_.sum():.1%}")

    metrics = {}

    print("\n  Training K-Means (k=8)...")
    km = MiniBatchKMeans(n_clusters=8, random_state=42, n_init=10, batch_size=4096)
    km_labels = km.fit_predict(X_reduced)
    sil_km = silhouette_score(X_reduced, km_labels, sample_size=10_000, random_state=42)
    db_km  = davies_bouldin_score(X_reduced, km_labels)
    print(f"    Silhouette     : {sil_km:.4f}  (higher is better)")
    print(f"    Davies-Bouldin : {db_km:.4f}  (lower is better)")
    metrics["kmeans"] = {"silhouette": round(sil_km, 4), "davies_bouldin": round(db_km, 4)}

    print("\n  Training HDBSCAN...")
    hdb = hdbscan.HDBSCAN(min_cluster_size=100, min_samples=10, core_dist_n_jobs=-1)
    hdb_labels = hdb.fit_predict(X_reduced)
    n_clusters = len(set(hdb_labels)) - (1 if -1 in hdb_labels else 0)
    noise_pct  = (hdb_labels == -1).mean()
    print(f"    Clusters found : {n_clusters}")
    print(f"    Noise points   : {noise_pct:.1%}")
    if n_clusters > 1:
        non_noise = hdb_labels != -1
        if non_noise.sum() > 1000:
            sil_hdb = silhouette_score(X_reduced[non_noise], hdb_labels[non_noise],
                                       sample_size=10_000, random_state=42)
            print(f"    Silhouette (non-noise) : {sil_hdb:.4f}")
            metrics["hdbscan"] = {"n_clusters": n_clusters, "noise_pct": round(float(noise_pct), 4),
                                   "silhouette": round(sil_hdb, 4)}
        else:
            metrics["hdbscan"] = {"n_clusters": n_clusters, "noise_pct": round(float(noise_pct), 4)}
    else:
        metrics["hdbscan"] = {"n_clusters": n_clusters, "noise_pct": round(float(noise_pct), 4)}

    print("\n  Saving clustering models...")
    for name, obj in [("kmeans_clusterer.pkl",  km),
                       ("hdbscan_clusterer.pkl", hdb),
                       ("cluster_scaler.pkl",    scaler),
                       ("cluster_pca.pkl",       pca)]:
        with open(output_dir / name, "wb") as f:
            pickle.dump(obj, f)
        print(f"    Saved -> {output_dir / name}")

    print("  Clustering complete.")
    return metrics


def train_classification(X_train, y_train, X_test, y_test, output_dir: Path) -> dict:
    import numpy as np
    import lightgbm as lgb
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import (roc_auc_score, accuracy_score,
                                  precision_score, recall_score, f1_score)
    from sklearn.model_selection import train_test_split

    banner("Classification (supervised)")
    metrics = {}

    train_mask = y_train != -1
    test_mask  = y_test  != -1
    X_tr, y_tr = X_train[train_mask], y_train[train_mask]
    X_te, y_te = X_test[test_mask],   y_test[test_mask]

    print(f"  Training rows : {X_tr.shape[0]:,}  |  Test rows : {X_te.shape[0]:,}")

    is_binary = len(np.unique(y_tr)) == 2

    X_tr2, X_val, y_tr2, y_val = train_test_split(
        X_tr, y_tr, test_size=0.1, stratify=y_tr, random_state=42
    )

    print("\n  Training LightGBM...")
    lgbm_params = {
        "objective":         "binary" if is_binary else "multiclass",
        "boosting":          "gbdt",
        "num_iterations":    500,
        "learning_rate":     0.1,
        "num_leaves":        64,
        "num_threads":       0,
        "seed":              42,
        "min_data_in_leaf":  100,
        "bagging_fraction":  0.9,
        "bagging_freq":      1,
        "feature_fraction":  0.9,
        "lambda_l2":         1.0,
        "is_unbalance":      True,
        "verbosity":         -1,
        "metric":            ["auc", "binary_logloss"] if is_binary else ["multi_logloss"],
        "first_metric_only": True,
    }
    if not is_binary:
        lgbm_params["num_class"] = int(np.max(y_tr)) + 1

    cat_features = [i for i in [2, 3, 4, 5, 6, 701, 702] if i < X_tr2.shape[1]]
    train_set = lgb.Dataset(X_tr2, y_tr2, categorical_feature=cat_features)
    val_set   = lgb.Dataset(X_val, y_val, reference=train_set, categorical_feature=cat_features)

    lgbm_model = lgb.train(
        lgbm_params, train_set, valid_sets=val_set,
        callbacks=[lgb.early_stopping(20, verbose=False), lgb.log_evaluation(50)],
    )

    y_pred_lgbm = lgbm_model.predict(X_te)
    if is_binary:
        y_class = (y_pred_lgbm > 0.5).astype(int)
        lgbm_metrics = {
            "roc_auc":   round(roc_auc_score(y_te, y_pred_lgbm), 4),
            "accuracy":  round(accuracy_score(y_te, y_class), 4),
            "precision": round(precision_score(y_te, y_class, zero_division=0), 4),
            "recall":    round(recall_score(y_te, y_class, zero_division=0), 4),
            "f1":        round(f1_score(y_te, y_class, zero_division=0), 4),
        }
    else:
        y_class = np.argmax(y_pred_lgbm, axis=1)
        lgbm_metrics = {
            "accuracy": round(accuracy_score(y_te, y_class), 4),
            "f1_macro": round(f1_score(y_te, y_class, average="macro", zero_division=0), 4),
        }

    print("\n  LightGBM results:")
    for k, v in lgbm_metrics.items():
        print(f"    {k:<14}: {v}")
    metrics["lgbm"] = lgbm_metrics

    lgbm_path = output_dir / "lgbm_classifier.model"
    lgbm_model.save_model(str(lgbm_path), num_iteration=lgbm_model.best_iteration)
    print(f"  Saved -> {lgbm_path}")

    MAX_RF_ROWS = 100_000
    if X_tr.shape[0] > MAX_RF_ROWS:
        idx = np.random.choice(X_tr.shape[0], MAX_RF_ROWS, replace=False)
        X_rf, y_rf = X_tr[idx], y_tr[idx]
    else:
        X_rf, y_rf = X_tr, y_tr

    print("\n  Training Random Forest (100 trees)...")
    rf = RandomForestClassifier(
        n_estimators=100, max_depth=20, min_samples_leaf=5,
        n_jobs=-1, random_state=42, class_weight="balanced",
    )
    rf.fit(X_rf, y_rf)

    y_pred_rf = rf.predict(X_te)
    if is_binary:
        y_prob_rf = rf.predict_proba(X_te)[:, 1]
        rf_metrics = {
            "roc_auc":   round(roc_auc_score(y_te, y_prob_rf), 4),
            "accuracy":  round(accuracy_score(y_te, y_pred_rf), 4),
            "precision": round(precision_score(y_te, y_pred_rf, zero_division=0), 4),
            "recall":    round(recall_score(y_te, y_pred_rf, zero_division=0), 4),
            "f1":        round(f1_score(y_te, y_pred_rf, zero_division=0), 4),
        }
    else:
        rf_metrics = {
            "accuracy": round(accuracy_score(y_te, y_pred_rf), 4),
            "f1_macro": round(f1_score(y_te, y_pred_rf, average="macro", zero_division=0), 4),
        }

    print("\n  Random Forest results:")
    for k, v in rf_metrics.items():
        print(f"    {k:<14}: {v}")
    metrics["random_forest"] = rf_metrics

    rf_path = output_dir / "random_forest_classifier.pkl"
    with open(rf_path, "wb") as f:
        pickle.dump(rf, f)
    print(f"  Saved -> {rf_path}")

    print("  Classification complete.")
    return metrics


def write_report(output_dir: Path, args, cluster_metrics: dict, class_metrics: dict) -> None:
    from datetime import datetime

    lines = [
        "EMBER2024 Training Report",
        "=" * 60,
        f"Date       : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"File type  : {args.file_type}",
        f"Label type : {args.label_type}",
        f"Max GB     : {args.max_gb}",
        "",
        "Clustering Metrics",
    ]
    for model, m in cluster_metrics.items():
        lines.append(f"  {model}:")
        for k, v in m.items():
            lines.append(f"    {k:<20}: {v}")
    lines += ["", "Classification Metrics"]
    for model, m in class_metrics.items():
        lines.append(f"  {model}:")
        for k, v in m.items():
            lines.append(f"    {k:<20}: {v}")

    report_path = output_dir / "training_report.txt"
    with open(report_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  Report saved -> {report_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="EMBER2024 Clustering & Classification Pipeline")
    parser.add_argument("--data-dir",        default="./ember_data")
    parser.add_argument("--output-dir",      default="./model")
    parser.add_argument("--file-type",       default="PDF",
                        choices=["PDF", "ELF", "APK", "Win32", "Win64", "Dot_Net", "PE", "all"])
    parser.add_argument("--split",           default="all",
                        choices=["all", "train", "test"])
    parser.add_argument("--label-type",      default="label",
                        choices=["label", "family", "behavior", "file_property", "packer", "exploit", "group"])
    parser.add_argument("--max-gb",          type=float, default=None,
                        help="Limit training data to this many GB (e.g. --max-gb 1)")
    parser.add_argument("--skip-download",   action="store_true")
    parser.add_argument("--skip-vectorize",  action="store_true")
    parser.add_argument("--skip-clustering", action="store_true")
    args = parser.parse_args()

    check_imports()
    import numpy as np
    import thrember

    data_dir   = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    banner("EMBER2024 Pipeline")
    print(f"  Data dir   : {data_dir}")
    print(f"  Output dir : {output_dir}")
    print(f"  File type  : {args.file_type}")
    print(f"  Label type : {args.label_type}")
    print(f"  Max GB     : {args.max_gb if args.max_gb else 'unlimited'}")

    if not args.skip_download:
        download_data(data_dir, args.file_type, args.split)

    if not args.skip_vectorize:
        vectorize_data(data_dir, args.label_type)

    banner("Loading features")
    X_train, y_train = thrember.read_vectorized_features(str(data_dir), "train")
    X_test,  y_test  = thrember.read_vectorized_features(str(data_dir), "test")
    print(f"  Train: {X_train.shape}  |  Test: {X_test.shape}")

    if args.max_gb:
        X_train, y_train = subsample_by_gb(X_train, y_train, args.max_gb)

    cluster_metrics = {}
    if not args.skip_clustering:
        cluster_metrics = train_clustering(X_train, output_dir)

    class_metrics = train_classification(X_train, y_train, X_test, y_test, output_dir)

    banner("Saving report")
    write_report(output_dir, args, cluster_metrics, class_metrics)

    banner("Done!")
    print(f"  Models saved to: {output_dir.resolve()}\n")


if __name__ == "__main__":
    main()