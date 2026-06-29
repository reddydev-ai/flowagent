"""The LangGraph workflow.

Flow:
  research -> check_documents -> assess_risk -> [interrupt: human approval] -> write_memo

Key production patterns demonstrated:
  - typed state (VendorState)
  - tool use (Tavily web search)
  - human-in-the-loop via interrupt() - the graph pauses at the approval gate and
    resumes only when a human sends approve/reject through the API
  - persistent checkpointing:
      * With DATABASE_URL set: PostgresSaver via psycopg connection (production-style)
      * Without DATABASE_URL: MemorySaver (zero-infra demo)
"""
from __future__ import annotations
from functools import lru_cache

from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt

from .config import get_settings
from .state import VendorState
from .tools import web_search

settings = get_settings()


@lru_cache
def _openai():
    """Lazy OpenAI client. Returns None when no key/package is available so the
    demo can still run deterministically in no-key mode."""
    if not settings.openai_api_key:
        return None
    try:
        from openai import OpenAI  # type: ignore
        return OpenAI(api_key=settings.openai_api_key)
    except Exception:
        return None


# ---------------- nodes ----------------

def research(state: VendorState) -> dict:
    vendor = state["vendor_name"]
    summary = web_search(f"{vendor} company background reputation compliance news")
    return {"research_summary": summary}


def check_documents(state: VendorState) -> dict:
    submitted = {d.strip().lower() for d in state.get("submitted_docs", [])}
    missing = [req for req in settings.required_docs if req.strip().lower() not in submitted]
    return {"missing_docs": missing}


def assess_risk(state: VendorState) -> dict:
    missing = state.get("missing_docs", [])
    research_summary = state.get("research_summary", "")

    # Deterministic base rule on documents
    if len(missing) == 0:
        base = "green"
    elif len(missing) <= 1:
        base = "yellow"
    else:
        base = "red"

    client = _openai()
    if client is None:
        rationale = (
            f"Document check produced a {base} risk rating. "
            f"Missing required documents: {missing or 'none'}. "
            "Public search is summarized separately and no LLM override was applied in no-key mode."
        )
        return {"risk_level": base, "risk_rationale": rationale}

    # LLM weighs public-info red flags and writes a rationale
    prompt = (
        f"Vendor: {state['vendor_name']}\n"
        f"Missing required documents: {missing or 'none'}\n"
        f"Document-based preliminary risk: {base}\n\n"
        f"Public information found:\n{research_summary}\n\n"
        "You are a vendor risk analyst. Considering BOTH missing documents and any "
        "red flags in the public information, output strictly in this format:\n"
        "RISK: <green|yellow|red>\n"
        "RATIONALE: <2-3 sentences>"
    )
    resp = client.chat.completions.create(
        model=settings.chat_model,
        temperature=0.0,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.choices[0].message.content.strip()

    risk = base
    rationale = text
    for line in text.splitlines():
        if line.upper().startswith("RISK:"):
            val = line.split(":", 1)[1].strip().lower()
            if val in {"green", "yellow", "red"}:
                risk = val
        if line.upper().startswith("RATIONALE:"):
            rationale = line.split(":", 1)[1].strip()

    return {"risk_level": risk, "risk_rationale": rationale}


def human_approval(state: VendorState) -> dict:
    """Pause and wait for a human.
    interrupt() serialises the payload to the caller and halts the graph.
    The value passed back via Command(resume=...) becomes the return value of
    interrupt() here, then we write it into state.
    """
    decision = interrupt(
        {
            "vendor_name": state["vendor_name"],
            "risk_level": state.get("risk_level"),
            "risk_rationale": state.get("risk_rationale"),
            "missing_docs": state.get("missing_docs", []),
            "prompt": (
                "Approve or reject this vendor. Resume with "
                "{'decision': 'approve'|'reject', 'comment': '...'}"
            ),
        }
    )
    return {
        "human_decision": decision.get("decision", "reject"),
        "human_comment": decision.get("comment", ""),
    }


def write_memo(state: VendorState) -> dict:
    prompt = (
        "Write a short, professional vendor verification memo.\n\n"
        f"Vendor: {state['vendor_name']}\n"
        f"Risk level: {state.get('risk_level')}\n"
        f"Rationale: {state.get('risk_rationale')}\n"
        f"Missing documents: {state.get('missing_docs', []) or 'none'}\n"
        f"Human decision: {state.get('human_decision')}\n"
        f"Reviewer comment: {state.get('human_comment') or 'none'}\n\n"
        "Format: Summary, Findings, Decision, Next steps. Under 200 words."
    )
    client = _openai()
    if client is None:
        return {
            "memo": (
                f"Summary: {state['vendor_name']} was reviewed through the vendor verification workflow.\n"
                f"Findings: Risk level is {state.get('risk_level')}; missing documents: "
                f"{state.get('missing_docs', []) or 'none'}.\n"
                f"Decision: Human reviewer selected {state.get('human_decision')}.\n"
                f"Next steps: {state.get('human_comment') or 'Complete required follow-up before onboarding.'}"
            )
        }

    resp = client.chat.completions.create(
        model=settings.chat_model,
        temperature=0.2,
        messages=[{"role": "user", "content": prompt}],
    )
    return {"memo": resp.choices[0].message.content.strip()}


# ---------------- checkpointer ----------------

def _make_checkpointer():
    """Return a checkpointer instance.

    With DATABASE_URL: PostgresSaver backed by a psycopg connection.
    Without: MemorySaver (in-memory, zero-infra, resets on restart).

    Why not use PostgresSaver.from_conn_string() context manager?
    It is a @contextmanager, so it only lives inside a 'with' block.
    For a long-lived FastAPI server we need a persistent connection instead.
    We create the psycopg connection directly and hand it to PostgresSaver.
    """
    if settings.database_url:
        try:
            import psycopg
            from langgraph.checkpoint.postgres import PostgresSaver
            conn = psycopg.connect(settings.database_url, autocommit=True)
            saver = PostgresSaver(conn)
            saver.setup()  # creates tables if they don't exist
            return saver
        except Exception as e:
            import warnings
            warnings.warn(
                f"PostgresSaver failed ({e}), falling back to MemorySaver. "
                "Check DATABASE_URL and psycopg installation."
            )
    from langgraph.checkpoint.memory import MemorySaver
    return MemorySaver()


# Build graph once at module level
def build_graph():
    g = StateGraph(VendorState)
    g.add_node("research", research)
    g.add_node("check_documents", check_documents)
    g.add_node("assess_risk", assess_risk)
    g.add_node("human_approval", human_approval)
    g.add_node("write_memo", write_memo)

    g.add_edge(START, "research")
    g.add_edge("research", "check_documents")
    g.add_edge("check_documents", "assess_risk")
    g.add_edge("assess_risk", "human_approval")
    g.add_edge("human_approval", "write_memo")
    g.add_edge("write_memo", END)

    return g.compile(checkpointer=_make_checkpointer())
