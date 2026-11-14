import numpy as np
from test_features import sample_orders

from ml import risk
from ml.features import ORDER_FEATURES
from ml.predictor import Predictor


def test_risk_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("CHAINSHIELD_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("CHAINSHIELD_ARTIFACTS_DIR", str(tmp_path / "artifacts"))
    orders = sample_orders(1200)
    late_rate = np.where(orders.shipping_mode == "First Class", 0.8, 0.4)
    orders["label"] = (np.random.default_rng(1).uniform(size=len(orders)) < late_rate).astype(int)
    orders["block"] = np.repeat(["train", "val", "s3"], [800, 200, 200])
    (tmp_path / "data/processed").mkdir(parents=True)
    orders.to_parquet(tmp_path / "data/processed/orders.parquet")

    risk.train(version=1)
    predictor = Predictor.load(tmp_path / "artifacts/risk/v1")

    rows = orders.head(3)
    probabilities = predictor.predict_proba(rows)
    assert probabilities.shape == (3, 2)
    assert np.allclose(probabilities.sum(axis=1), 1)
    explanations = predictor.explain(rows, top=5)
    assert len(explanations) == 3 and len(explanations[0]) == 5
    assert explanations[0][0][0].split("=")[0] in ORDER_FEATURES
