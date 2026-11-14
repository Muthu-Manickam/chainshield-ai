"""DataCo item rows -> one row per order with time blocks; CrisisMMD -> tweets with labels, splits and queue pool."""

import json
import os
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[2]
BLOCKS = [("train", 0.60), ("val", 0.70), ("s1", 0.75), ("s2", 0.80), ("s3", 0.85), ("test", 1.00)]
CATEGORY_MERGE = {
    "infrastructure_and_utility_damage": "infrastructure",
    "vehicle_damage": "infrastructure",
    "affected_individuals": "affected_people",
    "injured_or_dead_people": "affected_people",
    "missing_or_found_people": "affected_people",
    "rescue_volunteering_or_donation_effort": "rescue_donation",
    "other_relevant_information": "other_relevant",
    "not_humanitarian": "not_humanitarian",
}


def data_dir() -> Path:
    return Path(os.environ.get("CHAINSHIELD_DATA_DIR", ROOT / "data"))


def artifacts_dir() -> Path:
    return Path(os.environ.get("CHAINSHIELD_ARTIFACTS_DIR", ROOT / "artifacts"))


def assign_blocks(dates: pd.Series) -> pd.Series:
    """Label each row train/val/s1/s2/s3/test by its position in date order."""
    position = dates.rank(method="first") / len(dates)
    edges = [0.0] + [edge for _, edge in BLOCKS]
    return pd.cut(position, edges, labels=[name for name, _ in BLOCKS]).astype(str)


def prepare_orders():
    items = pd.read_csv(data_dir() / "raw/dataco/DataCoSupplyChainDataset.csv", encoding="latin-1")
    items = items[~items["Order Status"].isin(["CANCELED", "SUSPECTED_FRAUD"])]
    items = items.sort_values("Order Item Total", ascending=False)
    orders = items.groupby("Order Id").agg(
        order_date=("order date (DateOrders)", "first"),
        market=("Market", "first"),
        region=("Order Region", "first"),
        country=("Order Country", "first"),
        shipping_mode=("Shipping Mode", "first"),
        scheduled_days=("Days for shipment (scheduled)", "first"),
        item_count=("Order Item Quantity", "sum"),
        order_value=("Order Item Total", "sum"),
        top_category=("Category Name", "first"),
        customer_segment=("Customer Segment", "first"),
        label=("Late_delivery_risk", "first"),
    )
    orders = orders.rename_axis("order_id").reset_index()
    orders["order_date"] = pd.to_datetime(orders["order_date"], format="%m/%d/%Y %H:%M")
    orders = orders.sort_values(["order_date", "order_id"], ignore_index=True)
    orders["block"] = assign_blocks(orders["order_date"])
    write(orders, "orders.parquet")
    print(f"orders: {len(orders)} (late rate {orders.label.mean():.3f})")
    mix = pd.crosstab(orders.block, orders.market, normalize="index").round(3)
    print(mix.assign(orders=orders.block.value_counts()).loc[[name for name, _ in BLOCKS]])


def read_splits() -> pd.DataFrame:
    """Official tweet-level split (the informative split files cover every tweet once per split)."""
    frames = []
    for split in ["train", "dev", "test"]:
        rows = json.loads((data_dir() / f"raw/crisismmd/splits/informative_{split}.json").read_text())
        ids = {str(row["tweet_id"]) for row in rows}
        frames.append(pd.DataFrame({"tweet_id": sorted(ids), "split": split}))
    return pd.concat(frames, ignore_index=True).drop_duplicates("tweet_id")


def prepare_tweets():
    events = sorted((data_dir() / "raw/crisismmd/events").glob("*.tsv"))
    rows = pd.concat([pd.read_csv(path, sep="\t", dtype={"tweet_id": str}) for path in events])
    tweets = pd.DataFrame({
        "tweet_id": rows["tweet_id"],
        "event": rows["image_path"].str.split("/").str[1],
        "text": rows["tweet_text"],
        "informative": (rows["text_info"] == "informative").astype(int),
        "category": rows["text_human"].map(CATEGORY_MERGE),
    }).drop_duplicates("tweet_id")
    tweets = tweets.merge(read_splits(), on="tweet_id")
    train = tweets[tweets.split == "train"]
    _, pool = train_test_split(train, test_size=0.15, stratify=train.event + "/" + train.category, random_state=42)
    _, holdout = train_test_split(pool, test_size=0.20, stratify=pool.category, random_state=42)
    tweets["pool"] = tweets.tweet_id.isin(pool.tweet_id)
    tweets["pool_holdout"] = tweets.tweet_id.isin(holdout.tweet_id)
    write(tweets, "tweets.parquet")
    print(f"tweets: {len(tweets)}, pool {tweets.pool.sum()}, pool holdout {tweets.pool_holdout.sum()}")
    print(pd.crosstab(tweets.category, tweets.split))


def write(frame: pd.DataFrame, name: str):
    out = data_dir() / "processed"
    out.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(out / name, index=False)
