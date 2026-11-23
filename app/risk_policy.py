"""Deterministic risk guardrail.

Public information may increase a risk classification but cannot override
mandatory missing-document rules to produce a lower-risk classification.
"""
from __future__ import annotations

RISK_ORDER = {"green": 0, "yellow": 1, "red": 2}


def enforce_risk_floor(document_risk: str, suggested_risk: str) -> str:
    if document_risk not in RISK_ORDER:
        raise ValueError("Invalid document-based risk classification")
    if suggested_risk not in RISK_ORDER:
        return document_risk
    return max((document_risk, suggested_risk), key=RISK_ORDER.__getitem__)
