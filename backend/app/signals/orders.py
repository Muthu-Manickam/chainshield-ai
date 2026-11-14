from pathlib import Path

import pandas as pd
from ml.features import ORDER_FEATURES
from sqlalchemy import String, cast, func, insert, or_, select, update
from sqlalchemy.orm import Session

from app.signals import registry
from app.signals.models import Order
from app.signals.schemas import OrderFilter, OrderStats, RiskSummary

BANDS = ("high", "medium", "low")
HIDDEN_BLOCKS = ("train", "val")
HIGH_SCORE = 0.7  # model metadata only stores the decision threshold, which is the low/medium edge


def load_orders(db: Session, path: Path) -> int:
    frame = pd.read_parquet(path)
    rows = frame.assign(
        order_region=frame["region"], order_total=frame["order_value"], late=frame["label"].astype(bool),
        features=frame[ORDER_FEATURES].to_dict("records"),
    )[["order_id", "order_date", "market", "order_region", "shipping_mode", "customer_segment", "order_total",
       "item_count", "features", "block", "late"]]
    db.execute(insert(Order), rows.to_dict("records"))
    db.commit()
    return len(rows)


def band(score: float, threshold: float) -> str:
    return "low" if score < threshold else "medium" if score < HIGH_SCORE else "high"


def score_orders(db: Session) -> int:
    """Score every order not yet scored by the champion, in one batch."""
    champion = registry.champion(db, "risk")
    if champion is None:
        return 0
    version, predictor = champion
    todo = db.execute(
        select(Order.id, Order.features).where(Order.model_version_id.is_distinct_from(version.id))
    ).all()
    if not todo:
        return 0
    frame = pd.DataFrame([features for _, features in todo])
    scores = predictor.predict_proba(frame)[:, 1]
    explanations = predictor.explain(frame, top=5)
    threshold = predictor.metadata["threshold"]
    db.execute(update(Order), [
        {
            "id": order_id, "risk_score": float(score), "risk_band": band(score, threshold),
            "model_version_id": version.id,
            "factors": [
                {"feature": name.split("=")[0], "value": features[name.split("=")[0]], "impact": impact}
                for name, impact in explanation
            ],
        }
        for (order_id, features), score, explanation in zip(todo, scores, explanations)
    ])
    db.commit()
    return len(todo)


def _where(filters: OrderFilter) -> list:
    conditions = []
    if not filters.include_trained:
        conditions.append(Order.block.not_in(HIDDEN_BLOCKS))
    if filters.market:
        conditions.append(Order.market == filters.market)
    if filters.shipping_mode:
        conditions.append(Order.shipping_mode == filters.shipping_mode)
    if filters.band:
        conditions.append(Order.risk_band == filters.band)
    if filters.q:
        conditions.append(or_(cast(Order.order_id, String).like(f"{filters.q}%"),
                              Order.order_region.ilike(f"%{filters.q}%")))
    return conditions


def search_orders(db: Session, filters: OrderFilter, page: int, page_size: int) -> tuple[list[Order], int]:
    where = _where(filters)
    total = db.scalar(select(func.count()).select_from(Order).where(*where))
    rows = db.scalars(
        select(Order).where(*where).order_by(Order.risk_score.desc().nulls_last(), Order.id)
        .offset((page - 1) * page_size).limit(page_size)
    ).all()
    return list(rows), total


def get_order(db: Session, order_id: int) -> Order | None:
    return db.scalar(select(Order).where(Order.order_id == order_id))


def _groups(db: Session, column, where: list) -> list[dict]:
    rows = db.execute(
        select(column, func.count(), *(func.count().filter(Order.risk_band == band) for band in BANDS))
        .where(*where).group_by(column).order_by(column)
    )
    return [{column.key: name, "total": total, **dict(zip(BANDS, counts))} for name, total, *counts in rows]


def risk_summary(db: Session, filters: OrderFilter) -> RiskSummary:
    where = _where(filters)
    total, high, medium, low, mean = db.execute(
        select(func.count(), *(func.count().filter(Order.risk_band == band) for band in BANDS),
               func.avg(Order.risk_score)).where(*where)
    ).one()
    return RiskSummary(total=total, high=high, medium=medium, low=low, mean_score=mean,
                       by_shipping_mode=_groups(db, Order.shipping_mode, where))


def order_stats(db: Session) -> OrderStats:
    summary = risk_summary(db, OrderFilter())
    return OrderStats(by_band={"low": summary.low, "medium": summary.medium, "high": summary.high},
                      by_shipping_mode=summary.by_shipping_mode)
