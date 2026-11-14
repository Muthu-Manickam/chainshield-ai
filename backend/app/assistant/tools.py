from sqlalchemy.orm import Session


def get_order(db: Session, order_id: int) -> dict:
    return {}  # STUB


def search_orders(db: Session, market: str | None = None, shipping_mode: str | None = None,
                  band: str | None = None) -> dict:
    return {}  # STUB


def risk_summary(db: Session, market: str | None = None, shipping_mode: str | None = None) -> dict:
    return {}  # STUB


def search_incidents(db: Session, status: str | None = None, label: str | None = None) -> dict:
    return {}  # STUB


def classify_text(db: Session, text: str) -> dict:
    return {}  # STUB


def search_guidance(db: Session, query: str) -> dict:
    return {}  # STUB


def get_investigation(db: Session, investigation_id: int) -> dict:
    return {}  # STUB


def model_info(db: Session, task: str) -> dict:
    return {}  # STUB


TOOLS: list = []  # STUB
