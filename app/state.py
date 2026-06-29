"""Typed graph state. Using a TypedDict (not a bare dict) is a production
requirement: every node knows exactly which fields it reads and writes.
"""
from __future__ import annotations
from typing import TypedDict, Literal


class VendorState(TypedDict, total=False):
    # --- inputs ---
    vendor_name: str
    submitted_docs: list[str]        # doc names the vendor actually provided

    # --- derived by nodes ---
    research_summary: str            # public info found via web search
    missing_docs: list[str]          # required docs not submitted
    risk_level: Literal["green", "yellow", "red"]
    risk_rationale: str

    # --- human-in-the-loop ---
    human_decision: Literal["approve", "reject"]
    human_comment: str

    # --- output ---
    memo: str
