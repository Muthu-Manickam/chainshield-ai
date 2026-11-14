import asyncio

import pytest
from fastapi import BackgroundTasks

from app.core.jobs import start_job
from tests.conftest import login_as

PARAMETER_FREE_GETS = [
    "/api/auth/me", "/api/users", "/api/users/audit", "/api/evals", "/api/orders", "/api/orders/stats",
    "/api/incidents", "/api/incidents/stats", "/api/models", "/api/knowledge/documents", "/api/knowledge/stats",
    "/api/investigations", "/api/investigations/stats", "/api/rules",
]

# --- B0 ---


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


@pytest.mark.parametrize(("role", "users", "decision"), [
    ("analyst", 403, 403), ("supervisor", 403, 404), ("admin", 200, 404),
])
def test_role_guards(client, role, users, decision):
    login_as(client, role)
    assert client.get("/api/users").status_code == users
    response = client.post("/api/investigations/1/actions/1/decision", json={"decision": "approved"})
    assert response.status_code == decision


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

# --- H1 ---
