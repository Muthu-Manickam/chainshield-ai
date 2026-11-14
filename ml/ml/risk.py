"""Order late-risk models: baselines, Logistic Regression, XGBoost, isotonic calibration, SHAP, metrics."""

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, f1_score, precision_recall_curve, roc_auc_score
from xgboost import XGBClassifier

from ml.data import artifacts_dir, data_dir
from ml.features import ORDER_FEATURES, order_matrix
from ml.predictor import Predictor

LEAKAGE_ALARM = 0.85
CANDIDATES = {
    "logreg": lambda: LogisticRegression(max_iter=2000),
    "xgboost": lambda: XGBClassifier(n_estimators=300, max_depth=5, learning_rate=0.05, subsample=0.8, random_state=0),
}


def model_dir(version: int) -> Path:
    return artifacts_dir() / "risk" / f"v{version}"


def best_threshold(y, p) -> float:
    """Threshold that maximises F1 on the given (validation) labels."""
    precision, recall, thresholds = precision_recall_curve(y, p)
    f1 = 2 * precision * recall / np.maximum(precision + recall, 1e-12)
    return float(thresholds[np.argmax(f1[:-1])])


def scores(y, p, threshold: float) -> dict:
    return {
        "roc_auc": round(roc_auc_score(y, p), 4),
        "pr_auc": round(average_precision_score(y, p), 4),
        "f1": round(f1_score(y, p >= threshold), 4),
        "brier": round(brier_score_loss(y, p), 4),
    }


def baseline_probas(train: pd.DataFrame, frame: pd.DataFrame) -> dict:
    """Majority class (constant late rate) and the late rate of each shipping mode."""
    mode_rate = train.groupby("shipping_mode")["label"].mean()
    return {
        "majority": np.full(len(frame), train["label"].mean()),
        "shipping_mode": frame["shipping_mode"].map(mode_rate).fillna(train["label"].mean()).to_numpy(),
    }


def fit_candidates(train: pd.DataFrame, val: pd.DataFrame, categories: dict) -> dict:
    """Fit each candidate on train, then isotonic-calibrate it on validation."""
    x_train, _ = order_matrix(train, categories)
    x_val, _ = order_matrix(val, categories)
    fitted = {}
    for name, make in CANDIDATES.items():
        base = make().fit(x_train, train["label"])
        calibrated = CalibratedClassifierCV(FrozenEstimator(base), method="isotonic").fit(x_val, val["label"])
        fitted[name] = (base, calibrated)
    return fitted


def evaluate_all(fitted: dict, train: pd.DataFrame, frames: dict, categories: dict) -> tuple[dict, dict]:
    """Metrics for baselines and candidates on each frame; thresholds are chosen on 'val'."""
    probas = {name: baseline_probas(train, frame) for name, frame in frames.items()}
    for name, frame in frames.items():
        x, _ = order_matrix(frame, categories)
        probas[name] |= {model: calibrated.predict_proba(x)[:, 1] for model, (_, calibrated) in fitted.items()}
    thresholds = {model: best_threshold(frames["val"]["label"], p) for model, p in probas["val"].items()}
    metrics = {
        name: {model: scores(frames[name]["label"], p, thresholds[model]) for model, p in models.items()}
        for name, models in probas.items()
    }
    return metrics, thresholds


def train(version: int, extra_blocks=()):
    orders = pd.read_parquet(data_dir() / "processed/orders.parquet")
    train_rows = orders[orders.block.isin(["train", *extra_blocks])]
    frames = {"val": orders[orders.block == "val"], "s3": orders[orders.block == "s3"]}
    _, categories = order_matrix(train_rows)
    fitted = fit_candidates(train_rows, frames["val"], categories)
    metrics, thresholds = evaluate_all(fitted, train_rows, frames, categories)
    for model, m in metrics["val"].items():
        if m["roc_auc"] > LEAKAGE_ALARM:
            raise RuntimeError(f"leakage alarm: {model} validation ROC-AUC {m['roc_auc']} > {LEAKAGE_ALARM}")
    best = max(CANDIDATES, key=lambda name: metrics["val"][name]["pr_auc"])
    base, calibrated = fitted[best]
    x_train, _ = order_matrix(train_rows, categories)
    background = x_train.sample(min(100, len(x_train)), random_state=0)
    out = model_dir(version)
    out.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": calibrated, "explainer": shap.Explainer(base, background)}, out / "model.joblib")
    metadata = {
        "task": "risk", "family": f"risk_{best}", "version": version, "classes": [0, 1],
        "features": ORDER_FEATURES, "categories": categories, "threshold": round(thresholds[best], 4),
        "trained_on": ["train", *extra_blocks], "train_rows": len(train_rows),
    }
    (out / "metadata.json").write_text(json.dumps(metadata, indent=2))
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2))
    print_metrics(metrics, best)


def evaluate_final(version: int):
    """Score the sealed test block once and add it to metrics.json."""
    out = model_dir(version)
    predictor = Predictor.load(out)
    test = pd.read_parquet(data_dir() / "processed/orders.parquet").query("block == 'test'")
    test_scores = scores(test["label"], predictor.predict_proba(test)[:, 1], predictor.metadata["threshold"])
    metrics = json.loads((out / "metrics.json").read_text()) | {"test": {predictor.family: test_scores}}
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2))
    print(f"risk v{version} test ({predictor.family}): {test_scores}")


def print_metrics(metrics: dict, best: str):
    for name, models in metrics.items():
        for model, m in models.items():
            mark = "  <- served" if model == best else ""
            print(f"{name:4} {model:14} ROC-AUC {m['roc_auc']:.4f}  PR-AUC {m['pr_auc']:.4f}  "
                  f"F1 {m['f1']:.4f}  Brier {m['brier']:.4f}{mark}")
