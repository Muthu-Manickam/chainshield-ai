"""Predictor: the one interface the backend uses to load a trained model, score rows and explain scores."""

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from ml.features import CATEGORICAL, order_matrix

RISK_FAMILIES = ("risk_logreg", "risk_xgboost")
TEXT_FAMILIES = ("tfidf", "bilstm", "distilbert")


class Predictor:
    def __init__(self, metadata: dict, payload: dict):
        self.metadata = metadata
        self.family = metadata["family"]
        self.classes = metadata["classes"]
        self.payload = payload

    @classmethod
    def load(cls, path) -> "Predictor":
        path = Path(path)
        metadata = json.loads((path / "metadata.json").read_text())
        if metadata["family"] in TEXT_FAMILIES:
            from ml.text import load_model  # imports torch, which risk-only callers never need

            return cls(metadata, {"model": load_model(path)})
        if metadata["family"] not in RISK_FAMILIES:
            raise ValueError(f"unknown model family: {metadata['family']}")
        return cls(metadata, joblib.load(path / "model.joblib"))

    def predict_proba(self, x: pd.DataFrame | list[str]) -> np.ndarray:
        """Class probabilities, one column per entry in `classes`; text models take a list of raw texts."""
        if self.family in TEXT_FAMILIES:
            return self.payload["model"].predict_proba(x)
        matrix, _ = order_matrix(x, self.metadata["categories"])
        return self.payload["model"].predict_proba(matrix)

    def explain(self, rows: pd.DataFrame, top: int = 5) -> list[list[tuple[str, float]]]:
        """Per row, the `top` features by absolute SHAP contribution (log-odds of late delivery)."""
        matrix, _ = order_matrix(rows, self.metadata["categories"])
        values = pd.DataFrame(self.payload["explainer"](matrix).values, columns=matrix.columns)
        by_feature = values.T.groupby(lambda column: column.split("=")[0], sort=False).sum().T
        explanations = []
        for (_, row), (_, contributions) in zip(rows.iterrows(), by_feature.iterrows()):
            ranked = contributions.reindex(contributions.abs().sort_values(ascending=False).index)[:top]
            explanations.append([
                (f"{feature}={row[feature]}" if feature in CATEGORICAL else feature, round(float(value), 4))
                for feature, value in ranked.items()
            ])
        return explanations
