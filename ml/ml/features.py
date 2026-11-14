"""Order feature allowlist, banned columns, and text cleaning, shared by training and serving."""

import re

import numpy as np
import pandas as pd

CATEGORICAL = ["market", "region", "country", "shipping_mode", "top_category", "customer_segment"]
NUMERIC = ["scheduled_days", "item_count", "order_value"]
ORDER_FEATURES = CATEGORICAL + NUMERIC
BANNED = [
    "Days for shipping (real)", "Delivery Status", "Order Status", "shipping date (DateOrders)", "Type",
    "Benefit per order", "Order Profit Per Order", "Order Item Profit Ratio",
    "Customer Email", "Customer Password", "Customer Fname", "Customer Lname", "Customer Street",
    "label", "block",
]
URL_OR_MENTION = re.compile(r"https?://\S+|@\w+|\bRT\b", re.IGNORECASE)


def order_matrix(df: pd.DataFrame, categories: dict | None = None) -> tuple[pd.DataFrame, dict]:
    """One-hot categoricals (unknown values -> all zeros) plus numerics; order_value is log1p-scaled.

    Pass the training `categories` when serving so columns match the fitted model."""
    if categories is None:
        categories = {col: sorted(df[col].dropna().unique().tolist()) for col in CATEGORICAL}
    parts = []
    for col in CATEGORICAL:
        known = pd.Categorical(df[col].where(df[col].isin(categories[col])), categories=categories[col])
        parts.append(pd.get_dummies(known, prefix=col, prefix_sep="=", dtype=float))
    numeric = df[NUMERIC].astype(float).assign(order_value=np.log1p(df["order_value"].astype(float)))
    matrix = pd.concat([part.set_axis(df.index) for part in parts] + [numeric], axis=1)
    return matrix, categories


def clean_text(text: str) -> str:
    return " ".join(URL_OR_MENTION.sub(" ", str(text)).lower().split())
