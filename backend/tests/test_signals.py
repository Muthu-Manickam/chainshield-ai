# --- S1 ---
import pandas as pd
import pytest
from ml.features import ORDER_FEATURES
from ml.predictor import Predictor
from sqlalchemy import func, select

from app.core.config import settings
from app.seed import seed_orders
from app.signals import orders, registry
from app.signals.models import ModelVersion, Order
from app.signals.schemas import OrderFilter
from tests.conftest import login_as


@pytest.fixture
def risk_predictor():
    return Predictor.load(settings.artifacts_dir / "risk" / "v1")


@pytest.fixture
def orders_parquet(tmp_path):
    frame = pd.read_parquet(settings.data_dir / "processed" / "orders.parquet")
    subset = pd.concat([frame[frame.block == "s1"].head(1000), frame[frame.block == "train"].head(1000)])
    path = tmp_path / "processed" / "orders.parquet"
    path.parent.mkdir()
    subset.to_parquet(path)
    return path


@pytest.fixture
def scored(db, orders_parquet, risk_predictor, monkeypatch):
    version = ModelVersion(task="risk", version=1, family=risk_predictor.family, artifact_path="risk/v1",
                           artifact_hash="test", metrics={}, status="champion")
    db.add(version)
    db.commit()
    monkeypatch.setattr(registry, "champion", lambda db, task: (version, risk_predictor))
    assert orders.load_orders(db, orders_parquet) == 2000
    assert orders.score_orders(db, version.id) == 2000
    return version


def test_s1_load_and_score(db, scored, risk_predictor):
    order = db.scalars(select(Order).where(Order.block == "s1").order_by(Order.id)).first()
    assert set(order.features) == set(ORDER_FEATURES)
    assert order.order_region == order.features["region"] and order.order_total == order.features["order_value"]
    assert order.late in (True, False) and order.released is False
    expected = risk_predictor.predict_proba(pd.DataFrame([order.features]))[0, 1]
    assert order.risk_score == pytest.approx(expected)
    assert order.model_version_id == scored.id
    assert len(order.factors) == 5 and set(order.factors[0]) == {"feature", "value", "impact"}
    threshold = risk_predictor.metadata["threshold"]
    assert all((o.risk_band == "low") == (o.risk_score < threshold) for o in db.scalars(select(Order)))
    assert {o.risk_band for o in db.scalars(select(Order))} == {"low", "medium", "high"}
    assert orders.score_orders(db, scored.id) == 0


def test_s1_search_hides_trained_blocks_and_filters(db, scored):
    rows, total = orders.search_orders(db, OrderFilter(), 1, 50)
    assert total == 1000 and len(rows) == 50 and {r.block for r in rows} == {"s1"}
    scores = [r.risk_score for r in rows]
    assert scores == sorted(scores, reverse=True)
    assert orders.search_orders(db, OrderFilter(include_trained=True), 1, 10)[1] == 2000
    high, high_total = orders.search_orders(db, OrderFilter(band="high"), 1, 5)
    assert high_total > 0 and {r.risk_band for r in high} == {"high"}
    mode = rows[0].shipping_mode
    assert {r.shipping_mode for r in orders.search_orders(db, OrderFilter(shipping_mode=mode), 1, 5)[0]} == {mode}
    assert orders.search_orders(db, OrderFilter(market="LATAM", q=str(rows[0].order_id)), 1, 5)[1] == 1
    assert orders.search_orders(db, OrderFilter(), 2, 50)[0][0].id != rows[0].id


def test_s1_summary_stats_and_detail(db, scored, client):
    summary = orders.risk_summary(db, OrderFilter())
    assert summary.total == 1000 == summary.high + summary.medium + summary.low
    assert sum(g["total"] for g in summary.by_shipping_mode) == 1000
    assert all(g["total"] == g["high"] + g["medium"] + g["low"] for g in summary.by_shipping_mode)
    assert 0 < summary.mean_score < 1
    assert orders.risk_summary(db, OrderFilter(include_trained=True)).total == 2000
    stats = orders.order_stats(db)
    assert stats.total == 1000 and stats.champion_version == 1
    assert stats.by_band == {"low": summary.low, "medium": summary.medium, "high": summary.high}
    assert [g["market"] for g in stats.by_market] == ["LATAM"]

    login_as(client, "analyst")
    order = db.scalars(select(Order)).first()
    detail = client.get(f"/api/orders/{order.order_id}")
    assert detail.status_code == 200 and len(detail.json()["factors"]) == 5
    assert client.get("/api/orders/999999999").status_code == 404
    assert client.get("/api/orders?band=high&page_size=3").json()["total"] == summary.high


def test_s1_seed_orders_is_idempotent(db, orders_parquet, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", orders_parquet.parents[1])
    seed_orders(db)
    seed_orders(db)
    assert db.scalar(select(func.count()).select_from(Order)) == 2000

# --- S2 ---

from ml.text import CLASSES, load_model

from app.core.models import AuditLog, User
from app.seed import seed_incidents
from app.signals import incidents
from app.signals.models import Incident


@pytest.fixture
def tweets_dir(tmp_path):
    tweets = pd.read_parquet(settings.data_dir / "processed" / "tweets.parquet")
    pool = tweets[tweets.pool & ~tweets.pool_holdout].head(12)
    others = [tweets[tweets.pool_holdout].head(2), tweets[tweets.split == "dev"].head(2)]
    (tmp_path / "processed").mkdir()
    pd.concat([pool, *others]).to_parquet(tmp_path / "processed" / "tweets.parquet")
    return tmp_path


@pytest.fixture
def incident_champion(db, monkeypatch):
    path = settings.artifacts_dir / "text" / "v1-tfidf"
    version = ModelVersion(task="incident", version=1, family="tfidf", artifact_path=str(path), artifact_hash="test",
                           metrics={}, status="champion")
    db.add(version)
    db.commit()
    model = load_model(path)
    monkeypatch.setattr(registry, "champion", lambda db, task: (version, model))
    return version


@pytest.fixture
def analyst(client, db):
    return db.scalar(select(User).where(User.email == "analyst@chainshield.local"))


def test_s2_load_pool_skips_holdout_and_is_idempotent(db, tweets_dir):
    path = tweets_dir / "processed" / "tweets.parquet"
    assert incidents.load_pool(db, path) == 12
    assert incidents.load_pool(db, path) == 0
    rows = list(db.scalars(select(Incident)))
    assert {(r.status, r.source) for r in rows} == {("pool", "pool")}
    assert all(r.gold_label in CLASSES and r.tweet_id and r.event for r in rows)


def test_s2_release_classifies_on_arrival(db, tweets_dir, incident_champion):
    incidents.load_pool(db, tweets_dir / "processed" / "tweets.parquet")
    released = incidents.release(db, 5)
    assert len(released) == 5
    assert all(r.status in ("classified", "needs_review") and r.predicted_label in CLASSES for r in released)
    assert all(0 < r.confidence <= 1 and 0 <= r.screening_score <= 1 for r in released)
    assert {r.model_version_id for r in released} == {incident_champion.id}
    assert len(incidents.release(db, 100)) == 7
    assert incidents.release(db, 5) == []


def test_s2_short_text_needs_review(db, incident_champion):
    result = incidents.classify_text(db, "flood help")
    assert result.needs_review and result.label in CLASSES
    long = incidents.classify_text(db, "the bridge collapsed after the flood and roads are destroyed")
    assert long.screening_score > 0.5


def test_s2_add_manual_rejects_evaluation_tweets(db, analyst, incident_champion):
    tweets = pd.read_parquet(settings.data_dir / "processed" / "tweets.parquet")
    dev_text = tweets[tweets.split == "dev"].text.iloc[0]
    with pytest.raises(ValueError):
        incidents.add_manual(db, dev_text.upper() + " https://t.co/abc", analyst)
    incident = incidents.add_manual(db, "Power lines are down across the whole district tonight", analyst)
    assert incident.source == "manual" and incident.tweet_id is None and incident.gold_label is None
    assert incident.status in ("classified", "needs_review") and incident.model_version_id == incident_champion.id


def test_s2_review_stats_and_audit(db, tweets_dir, analyst, incident_champion):
    incidents.load_pool(db, tweets_dir / "processed" / "tweets.parquet")
    first = incidents.release(db, 4)[0]
    reviewed = incidents.review(db, first.id, "rescue_donation", analyst)
    assert (reviewed.status, reviewed.reviewed_label, reviewed.review_source) == ("reviewed", "rescue_donation", "analyst")
    assert reviewed.reviewed_by == analyst.id and reviewed.reviewed_at
    assert db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.action == "incident.review")) == 1
    assert incidents.review(db, 999999, "other_relevant", analyst) is None
    with pytest.raises(ValueError):
        incidents.review(db, first.id, "nonsense", analyst)
    stats = incidents.incident_stats(db)
    assert stats.by_status["reviewed"] == 1 and sum(stats.by_status.values()) == 12
    assert stats.by_label["rescue_donation"] >= 1 and stats.reviews_since_champion == 1
    assert stats.needs_review == stats.by_status.get("needs_review", 0)
    rows, total = incidents.search_incidents(db, "reviewed", "rescue_donation", 1)
    assert total == 1 and rows[0].id == first.id
    assert incidents.search_incidents(db, None, None, 1)[1] == 4  # unreleased pool rows are hidden by default


def test_s2_release_gold_keeps_analyst_reviews(db, tweets_dir, analyst, incident_champion):
    incidents.load_pool(db, tweets_dir / "processed" / "tweets.parquet")
    first = incidents.release(db, 3)[0]
    incidents.review(db, first.id, "other_relevant", analyst)
    assert incidents.release_gold(db, analyst) == 11
    rows = {r.id: r for r in db.scalars(select(Incident))}
    assert rows[first.id].review_source == "analyst" and rows[first.id].reviewed_label == "other_relevant"
    others = [r for r in rows.values() if r.id != first.id]
    assert all(r.review_source == "batch" and r.reviewed_label == r.gold_label for r in others)
    assert incidents.release_gold(db, analyst) == 0


def test_s2_reclassify_touches_only_unreviewed(db, tweets_dir, analyst, incident_champion):
    incidents.load_pool(db, tweets_dir / "processed" / "tweets.parquet")
    first, second, _ = incidents.release(db, 3)
    incidents.review(db, first.id, "other_relevant", analyst)
    second.predicted_label = "stale"
    db.commit()
    assert incidents.reclassify_unreviewed(db, incident_champion.id) == 2
    db.refresh(second)
    assert second.predicted_label in CLASSES and first.status == "reviewed"


def test_s2_seed_incidents_releases_forty_once(db, tweets_dir, incident_champion, monkeypatch):
    big = pd.read_parquet(settings.data_dir / "processed" / "tweets.parquet")
    (tweets_dir / "processed").mkdir(exist_ok=True)
    big.to_parquet(tweets_dir / "processed" / "tweets.parquet")
    monkeypatch.setattr(settings, "data_dir", tweets_dir)
    seed_incidents(db)
    seed_incidents(db)
    pool = int((big.pool & ~big.pool_holdout).sum())
    assert db.scalar(select(func.count()).select_from(Incident)) == pool
    assert db.scalar(select(func.count()).select_from(Incident).where(Incident.status != "pool")) == 40


def test_s2_api_duplicate_is_409(client, incident_champion):
    from tests.conftest import login_as

    login_as(client, "analyst")
    tweets = pd.read_parquet(settings.data_dir / "processed" / "tweets.parquet")
    dup = client.post("/api/incidents", json={"text": tweets[tweets.split == "test"].text.iloc[0]})
    assert dup.status_code == 409
    ok = client.post("/api/incidents", json={"text": "Shelters are full and families need blankets and water"})
    assert ok.status_code == 200 and ok.json()["source"] == "manual"
    assert client.get("/api/incidents/stats").json()["by_status"]

# --- RG1 ---

from app.seed import seed_models

RISK_V1 = settings.artifacts_dir / "risk" / "v1"


def test_rg1_first_version_is_champion(db):
    first = registry.register_version(db, "risk", RISK_V1)
    second = registry.register_version(db, "risk", RISK_V1)
    assert (first.version, first.status, second.version, second.status) == (1, "champion", 2, "candidate")
    assert first.promoted_at and first.artifact_hash == second.artifact_hash
    assert [v.version for v in registry.list_versions(db, "risk")] == [2, 1]
    assert registry.list_versions(db, "incident") == []


def test_rg1_risk_champion_is_cached_and_scores(db):
    assert registry.champion(db, "risk") is None
    registry.register_version(db, "risk", RISK_V1)
    version, predictor = registry.champion(db, "risk")
    assert registry.champion(db, "risk")[1] is predictor
    rows = pd.read_parquet(settings.data_dir / "processed" / "orders.parquet").head(3)
    assert predictor.predict_proba(rows).shape == (3, 2)
    assert registry.model_info(db, "risk")["champion"]["id"] == version.id


def test_rg1_seed_models_registers_both_champions_once(db):
    seed_models(db)
    seed_models(db)
    versions = registry.list_versions(db, None)
    assert [(v.task, v.family, v.status) for v in versions] == [
        ("incident", "tfidf", "champion"), ("risk", "risk_xgboost", "champion")]
    _, model = registry.champion(db, "incident")
    assert model.predict_proba(["the bridge collapsed after the flood"]).shape == (1, 5)
    assert registry.model_info(db, "incident")["versions"] == 1

# --- RG2 ---
