"""End-to-end offline API lifecycle and authorization checks.

External LLM, search and database credentials are intentionally absent.
Exercise the real LangGraph workflow with in-memory checkpointing.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app import security


@pytest.fixture
def client(monkeypatch):
    class DemoCredentials:
        api_key = "test-api-secret"
        reviewer_api_key = "different-reviewer-secret"

    monkeypatch.setattr(security, "get_settings", lambda: DemoCredentials)
    with TestClient(app) as instance:
        yield instance


def test_start_requires_api_authentication(client):
    r = client.post("/verify", json={
        "vendor_name": "Demo Supplier",
        "submitted_docs": [],
    })
    assert r.status_code == 401


def test_approval_requires_distinct_reviewer_authorization(client):
    headers = {"X-API-Key": "test-api-secret"}
    start = client.post("/verify", headers=headers, json={
        "vendor_name": "Demo Supplier",
        "submitted_docs": ["GST/HST Registration"],
    })
    assert start.status_code == 200, start.text
    payload = start.json()
    assert payload["status"] == "awaiting_approval"
    assert payload["approval_request"]["risk_level"] == "red"

    resume_data = {
        "thread_id": payload["thread_id"],
        "decision": "reject",
        "comment": "Documents incomplete",
    }
    unauthorized = client.post("/verify/resume", headers=headers, json=resume_data)
    assert unauthorized.status_code == 403

    authorized = client.post(
        "/verify/resume",
        headers={**headers, "X-Reviewer-Key": "different-reviewer-secret"},
        json=resume_data,
    )
    assert authorized.status_code == 200, authorized.text
    assert authorized.json()["decision"] == "reject"
    assert authorized.json()["risk_level"] == "red"
    assert "memo" in authorized.json()

    repeat = client.post(
        "/verify/resume",
        headers={**headers, "X-Reviewer-Key": "different-reviewer-secret"},
        json=resume_data,
    )
    assert repeat.status_code == 409


def test_invalid_approval_rejected(client):
    r = client.post("/verify/resume",
                    headers={"X-API-Key": "test-api-secret", "X-Reviewer-Key": "different-reviewer-secret"},
                    json={"thread_id": "unknown", "decision": "maybe"})
    assert r.status_code == 400
