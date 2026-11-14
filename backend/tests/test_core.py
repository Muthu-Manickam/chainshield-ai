import asyncio

import pytest
from fastapi import BackgroundTasks
from fastapi.testclient import TestClient

from app.core.jobs import start_job
from app.main import app
from tests.conftest import login_as

PARAMETER_FREE_GETS = [
    "/api/auth/me", "/api/users", "/api/users/audit", "/api/evals", "/api/orders", "/api/orders/stats",
    "/api/incidents", "/api/incidents/stats", "/api/models", "/api/knowledge/documents",
    "/api/investigations", "/api/investigations/stats", "/api/rules",
]


def test_login_sets_cookie_and_me_returns_user(client):
    user = login_as(client, "analyst")
    assert user["role"] == "analyst"
    assert client.get("/api/auth/me").json()["email"] == "analyst@chainshield.local"
    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401


def test_wrong_password_is_rejected(client):
    response = client.post("/api/auth/login", json={"email": "admin@chainshield.local", "password": "nope"})
    assert response.status_code == 401
    assert client.get("/api/auth/me").status_code == 401


def test_creating_a_user_writes_an_audit_row(client):
    login_as(client, "admin")
    created = client.post("/api/users", json={"email": "new@chainshield.local", "password": "pw", "role": "analyst"})
    assert created.status_code == 200
    duplicate = client.post("/api/users", json={"email": "new@chainshield.local", "password": "pw", "role": "analyst"})
    assert duplicate.status_code == 409
    audit = client.get("/api/users/audit").json()
    assert audit[0]["action"] == "create" and audit[0]["entity_id"] == str(created.json()["id"])


def test_job_success_and_failure(client, db):
    def succeed(db, value):
        return {"value": value}

    def fail(db):
        raise RuntimeError("boom")

    background = BackgroundTasks()
    ok = start_job(db, background, "test", succeed, 7)
    broken = start_job(db, background, "test", fail)
    asyncio.run(background())
    login_as(client, "analyst")
    assert client.get(f"/api/jobs/{ok.id}").json() | {"id": 0} == {
        "id": 0, "kind": "test", "status": "done", "log": "", "error": None, "result": {"value": 7}}
    failed = client.get(f"/api/jobs/{broken.id}").json()
    assert failed["status"] == "failed" and failed["error"] == "RuntimeError: boom"


@pytest.mark.parametrize("path", PARAMETER_FREE_GETS)
def test_parameter_free_gets_return_200(client, path):
    login_as(client, "admin")
    assert client.get(path).status_code == 200


# (method, path, body, lowest role allowed); auth/login and auth/logout are public by design
ROUTES = [
    ("GET", "/api/auth/me", None, "analyst"),
    ("GET", "/api/users", None, "admin"),
    ("POST", "/api/users", {"email": "x@chainshield.local", "password": "pw", "role": "analyst"}, "admin"),
    ("PATCH", "/api/users/1", {"is_active": True}, "admin"),
    ("GET", "/api/users/audit", None, "admin"),
    ("GET", "/api/jobs/1", None, "analyst"),
    ("GET", "/api/evals", None, "analyst"),
    ("GET", "/api/orders", None, "analyst"),
    ("GET", "/api/orders/stats", None, "analyst"),
    ("GET", "/api/orders/1", None, "analyst"),
    ("GET", "/api/incidents", None, "analyst"),
    ("POST", "/api/incidents", {"text": "bridge collapsed near the port"}, "analyst"),
    ("POST", "/api/incidents/release", {"count": 1}, "analyst"),
    ("POST", "/api/incidents/release-gold", None, "admin"),
    ("POST", "/api/incidents/1/review", {"label": "other_relevant"}, "analyst"),
    ("GET", "/api/incidents/stats", None, "analyst"),
    ("GET", "/api/models", None, "analyst"),
    ("POST", "/api/models/release-batch", {"block": "s1"}, "admin"),
    ("POST", "/api/models/retrain", {"task": "risk", "family": "lr"}, "admin"),
    ("POST", "/api/models/1/promote", None, "admin"),
    ("GET", "/api/knowledge/search?q=delay", None, "analyst"),
    ("GET", "/api/knowledge/documents", None, "analyst"),
    ("POST", "/api/knowledge/documents", None, "admin"),
    ("GET", "/api/investigations", None, "analyst"),
    ("POST", "/api/investigations", {"incident_id": 1, "scope": {}}, "analyst"),
    ("GET", "/api/investigations/stats", None, "analyst"),
    ("GET", "/api/investigations/1", None, "analyst"),
    ("GET", "/api/investigations/1/stream", None, "analyst"),
    ("POST", "/api/investigations/1/actions/1/decision", {"decision": "approved"}, "supervisor"),
    ("POST", "/api/chat", {"message": "hello"}, "analyst"),
    ("GET", "/api/chat/none", None, "analyst"),
    ("GET", "/api/rules", None, "analyst"),
    ("PUT", "/api/rules/1", {"cost_usd": 1}, "admin"),
]
ROLE_RANK = {"analyst": 0, "supervisor": 1, "admin": 2}


@pytest.mark.parametrize(("method", "path", "body", "lowest"), ROUTES, ids=[f"{m} {p}" for m, p, _, _ in ROUTES])
def test_h1_role_matrix(client, method, path, body, lowest):
    def call(session):
        return session.request(method, path, json=body)

    with TestClient(app, raise_server_exceptions=False) as anonymous:
        assert call(anonymous).status_code == 401
    for role, rank in ROLE_RANK.items():
        with TestClient(app, raise_server_exceptions=False) as session:
            login_as(session, role)
            status = call(session).status_code
            if rank < ROLE_RANK[lowest]:
                assert status == 403, f"{role} should be forbidden"
            else:
                assert status not in (401, 403), f"{role} should be allowed, got {status}"
