"""Offline security tests; no LLM credentials or external service required."""
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app import security
from app.risk_policy import enforce_risk_floor


def test_api_is_fail_closed_without_configured_secret(monkeypatch):
    monkeypatch.setattr(security, "get_settings", lambda: SimpleNamespace(api_key="", reviewer_api_key=""))
    with pytest.raises(HTTPException) as exc:
        security.require_api_key("anything")
    assert exc.value.status_code == 503


@pytest.mark.parametrize("presented", [None, "", "wrong"])
def test_api_rejects_missing_or_wrong_secret(monkeypatch, presented):
    monkeypatch.setattr(security, "get_settings", lambda: SimpleNamespace(api_key="sample-api-key", reviewer_api_key="sample-review-key"))
    with pytest.raises(HTTPException) as exc:
        security.require_api_key(presented)
    assert exc.value.status_code == 401


def test_api_accepts_correct_secret(monkeypatch):
    monkeypatch.setattr(security, "get_settings", lambda: SimpleNamespace(api_key="sample-api-key", reviewer_api_key="sample-review-key"))
    assert security.require_api_key("sample-api-key") is None


def test_reviewer_authorization_is_independent(monkeypatch):
    monkeypatch.setattr(security, "get_settings", lambda: SimpleNamespace(api_key="api-secret", reviewer_api_key="review-secret"))
    with pytest.raises(HTTPException) as exc:
        security.require_reviewer_key("api-secret")
    assert exc.value.status_code == 403
    assert security.require_reviewer_key("review-secret") is None


def test_missing_reviewer_secret_fails_closed(monkeypatch):
    monkeypatch.setattr(security, "get_settings", lambda: SimpleNamespace(api_key="api-secret", reviewer_api_key=""))
    with pytest.raises(HTTPException) as exc:
        security.require_reviewer_key("anything")
    assert exc.value.status_code == 503


@pytest.mark.parametrize(("document_risk", "proposed", "expected"), [
    ("red", "green", "red"),
    ("red", "yellow", "red"),
    ("yellow", "green", "yellow"),
    ("green", "red", "red"),
    ("green", "yellow", "yellow"),
    ("green", "green", "green"),
    ("yellow", "invalid", "yellow"),
])
def test_llm_cannot_lower_document_risk(document_risk, proposed, expected):
    assert enforce_risk_floor(document_risk, proposed) == expected


def test_invalid_base_risk_is_rejected():
    with pytest.raises(ValueError):
        enforce_risk_floor("unknown", "green")
