"""FastAPI surface for FlowAgent.

The agent pauses for human approval, so the API is two-step:
  POST /verify         -> start a run; returns a thread_id and the approval request
  POST /verify/resume  -> send approve/reject for that thread_id; returns final memo

This start/pause/resume shape is exactly how human-in-the-loop agents are wired in
production: the run is persisted by thread_id and resumed later by a reviewer.
"""
from __future__ import annotations
import uuid

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from langgraph.types import Command

from .config import get_settings
from .graph import build_graph
from .security import require_api_key, require_reviewer_key

settings = get_settings()
app = FastAPI(title="FlowAgent", version="1.0.0",
              description="Agentic vendor verification with tool use and human-in-the-loop approval.")

GRAPH = build_graph()


class VerifyRequest(BaseModel):
    vendor_name: str
    submitted_docs: list[str] = []


class ResumeRequest(BaseModel):
    thread_id: str
    decision: str           # "approve" or "reject"
    comment: str = ""


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "persistent": bool(settings.database_url)}


@app.post("/verify")
def verify(req: VerifyRequest, _auth: None = Depends(require_api_key)) -> dict:
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    GRAPH.invoke(
        {"vendor_name": req.vendor_name, "submitted_docs": req.submitted_docs},
        config=config,
    )
    # When the graph pauses at interrupt(), the payload is NOT in the invoke()
    # return value. We read it from the persisted graph state instead: snap.next
    # is non-empty while paused, and the pending task holds the interrupt value.
    snap = GRAPH.get_state(config)
    if snap.next and snap.tasks and snap.tasks[0].interrupts:
        payload = snap.tasks[0].interrupts[0].value
        return {"thread_id": thread_id, "status": "awaiting_approval", "approval_request": payload}
    # No interrupt (shouldn't happen in this graph) -> already finished.
    return {"thread_id": thread_id, "status": "done", "memo": snap.values.get("memo")}


@app.post("/verify/resume")
def resume(req: ResumeRequest, _auth: None = Depends(require_api_key), _reviewer: None = Depends(require_reviewer_key)) -> dict:
    if req.decision not in {"approve", "reject"}:
        raise HTTPException(status_code=400, detail="decision must be 'approve' or 'reject'")
    config = {"configurable": {"thread_id": req.thread_id}}
    snapshot = GRAPH.get_state(config)
    if not snapshot.next or not snapshot.tasks or not snapshot.tasks[0].interrupts:
        raise HTTPException(status_code=409, detail="No pending approval for this thread.")
    result = GRAPH.invoke(
        Command(resume={"decision": req.decision, "comment": req.comment}),
        config=config,
    )
    return {
        "thread_id": req.thread_id,
        "status": "done",
        "risk_level": result.get("risk_level"),
        "missing_docs": result.get("missing_docs"),
        "decision": result.get("human_decision"),
        "memo": result.get("memo"),
    }
