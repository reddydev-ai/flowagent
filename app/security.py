"""Fail-closed API authentication for the portfolio demo.

These shared keys are for a controlled demonstration, not a substitute for
identity-aware authorization, reviewer roles, TLS, and audit logs in production.
"""
from __future__ import annotations

import secrets

from fastapi import Header, HTTPException

from .config import get_settings


def _check_key(presented: str | None, expected: str, *, reviewer: bool = False) -> None:
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="API authentication is not configured on the server.",
        )
    if presented is None or not secrets.compare_digest(presented, expected):
        raise HTTPException(
            status_code=403 if reviewer else 401,
            detail="Reviewer authorization required." if reviewer else "Unauthorized.",
        )


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Require X-API-Key for all business API operations."""
    _check_key(x_api_key, get_settings().api_key)


def require_reviewer_key(x_reviewer_key: str | None = Header(default=None)) -> None:
    """Require an independent X-Reviewer-Key before resuming an approval."""
    _check_key(x_reviewer_key, get_settings().reviewer_api_key, reviewer=True)
