from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.signals.models import Order
from app.signals.schemas import OrderFilter, OrderRow, OrderStats, RiskSummary


def load_orders(db: Session, csv_path: Path) -> int:
    return 0  # STUB


def score_orders(db: Session, version_id: int) -> int:
    return 0  # STUB


def search_orders(db: Session, filters: OrderFilter, page: int, page_size: int) -> tuple[list, int]:
    # STUB: three fixture rows for the CP1 probe
    rows = [
        OrderRow(id=n, order_id=1000 + n, order_date=datetime(2017, 1, n), market="Europe",
                 order_region="Western Europe", shipping_mode="Standard Class", customer_segment="Consumer",
                 order_total=100.0 * n, block="s1", risk_score=0.3 * n, risk_band=("low", "medium", "high")[n - 1])
        for n in (1, 2, 3)
    ]
    return rows, len(rows)


def get_order(db: Session, order_id: int) -> Order | None:
    return None  # STUB


def risk_summary(db: Session, filters: OrderFilter) -> RiskSummary:
    return RiskSummary(total=0, high=0, medium=0, low=0, mean_score=None, by_shipping_mode=[])  # STUB


def order_stats(db: Session) -> OrderStats:
    return OrderStats(total=0, by_band={}, by_market=[], by_shipping_mode=[], champion_version=None)  # STUB
