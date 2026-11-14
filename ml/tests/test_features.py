import numpy as np
import pandas as pd

from ml.data import assign_blocks
from ml.features import BANNED, ORDER_FEATURES, clean_text, order_matrix


def sample_orders(n: int = 50) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    return pd.DataFrame({
        "market": rng.choice(["LATAM", "Europe"], n),
        "region": rng.choice(["South America", "Western Europe"], n),
        "country": rng.choice(["Brasil", "Francia"], n),
        "shipping_mode": rng.choice(["Standard Class", "First Class"], n),
        "top_category": rng.choice(["Cleats", "Fishing"], n),
        "customer_segment": rng.choice(["Consumer", "Corporate"], n),
        "scheduled_days": rng.integers(0, 5, n),
        "item_count": rng.integers(1, 6, n),
        "order_value": rng.uniform(10, 500, n),
        "label": rng.integers(0, 2, n),
        "Delivery Status": "Late delivery",
        "Days for shipping (real)": 6,
    })


def test_allowlist_has_no_banned_column():
    assert not set(ORDER_FEATURES) & set(BANNED)


def test_order_matrix_uses_only_allowed_features():
    matrix, _ = order_matrix(sample_orders())
    sources = {column.split("=")[0] for column in matrix.columns}
    assert sources == set(ORDER_FEATURES)
    assert not sources & set(BANNED)


def test_order_matrix_serving_matches_training_columns():
    train, categories = order_matrix(sample_orders())
    serve, _ = order_matrix(sample_orders(3).assign(market="Unseen market"), categories)
    assert list(serve.columns) == list(train.columns)
    assert serve.filter(like="market=").sum().sum() == 0


def test_blocks_follow_date_order_and_sizes():
    dates = pd.Series(pd.date_range("2016-01-01", periods=1000, freq="h")).sample(frac=1, random_state=0)
    blocks = assign_blocks(dates)
    shares = blocks.value_counts(normalize=True)
    expected = {"train": 0.60, "val": 0.10, "s1": 0.05, "s2": 0.05, "s3": 0.05, "test": 0.15}
    assert {name: round(share, 2) for name, share in shares.items()} == expected
    order = ["train", "val", "s1", "s2", "s3", "test"]
    last_dates = [dates[blocks == name].max() for name in order]
    assert last_dates == sorted(last_dates)


def test_clean_text():
    assert clean_text("RT @Cal_OES: Fire NOW https://t.co/x") == ": fire now"
