import os

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://chainshield:chainshield@localhost:55432/cs_b0")
os.environ["LLM_MODE"] = "replay"

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.core.db import Base, SessionLocal, engine
from app.main import app
from app.seed import DEMO_PASSWORD, seed_users


def create_database(url: str) -> None:
    url = make_url(url)
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        if not conn.scalar(text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": url.database}):
            conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    admin.dispose()


@pytest.fixture(scope="session", autouse=True)
def database():
    create_database(os.environ["DATABASE_URL"])
    command.upgrade(Config(str(Path(__file__).parents[1] / "alembic.ini")), "head")


@pytest.fixture(autouse=True)
def clean_tables():
    yield
    tables = ", ".join(table.name for table in Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


@pytest.fixture
def client(db):
    seed_users(db)
    with TestClient(app) as test_client:
        yield test_client


def login_as(client: TestClient, role: str) -> dict:
    response = client.post("/api/auth/login", json={"email": f"{role}@chainshield.local", "password": DEMO_PASSWORD})
    assert response.status_code == 200, response.text
    return response.json()
