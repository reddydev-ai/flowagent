# FlowAgent — Vendor Verification Agent

> **AI product management perspective:** Automate investigation and document checks, but keep consequential decisions with a human reviewer. [Portfolio overview](https://github.com/reddydev-ai/guardeval/blob/main/PORTFOLIO.md) · [Product case study](docs/PRODUCT_CASE_STUDY.md) · [Technical setup](#setup)

**What this shows:** an independent agentic vendor-verification prototype with a deterministic document-risk floor, LangGraph pause/resume and distinct API/reviewer credentials. The key product decision is *automation with accountable human control*. **The prototype does not prove vendor risk accuracy in real deployments or measured onboarding savings.**

| Product question | Decision | Evidence |
| --- | --- | --- |
| Who authorizes a final outcome? | Pause the graph for an explicit human decision | [Workflow graph](app/graph.py) |
| Can AI override document-based risk? | Retain a deterministic minimum risk rating | [Risk guardrail](app/risk_policy.py) |
| Can anyone replay an approval? | Reject unauthorized reviewer keys and repeated resume | [Real API integration tests](tests/test_api_integration.py) |

An agentic workflow that verifies a supplier end-to-end: it can **research** the
vendor on the public web when the external research service is configured, **checks** which required compliance documents are
missing, produces a **green/yellow/red risk decision**, **pauses for human
approval**, and then writes a final **memo**.

Built on **LangGraph** with real human-in-the-loop control.

## Why it's built this way

| Decision | Reason |
|---|---|
| **LangGraph (not a plain chain)** | The workflow needs explicit state, branching, and the ability to *pause and resume*. Chains can't pause for a human. |
| **Typed state (`VendorState`)** | Every node declares what it reads/writes — debuggable and safe. |
| **`interrupt()` human-in-the-loop** | The graph genuinely halts at the approval gate and only continues when a reviewer sends approve/reject. High-stakes actions shouldn't be fully autonomous. |
| **Persistent checkpointing** | With `DATABASE_URL` set, a paused run is stored in Postgres and survives a process restart — resumed later by `thread_id`. Falls back to in-memory for zero-infra demos. |
| **Deterministic rule + LLM judgment** | Document completeness is a hard rule; public-info red flags are weighed by the LLM. Neither alone is enough. |

## Architecture

```
START
  │
  ▼ research            → Tavily web search (public info on the vendor)
  ▼ check_documents     → compare submitted docs vs required list → missing[]
  ▼ assess_risk         → deterministic doc rule + GPT-4o red-flag judgment → green/yellow/red
  ▼ human_approval      → interrupt()  ⏸  (waits for reviewer: approve/reject)
  ▼ write_memo          → GPT-4o final memo (summary, findings, decision, next steps)
END
        │
        ▼ checkpointer: PostgresSaver (if DATABASE_URL) else MemorySaver
```

## Security and deployment status

**Portfolio demo; not production approved.** API access requires `FLOWAGENT_API_KEY` via `X-API-Key` and approval resumes additionally require the independent `FLOWAGENT_REVIEWER_KEY` via `X-Reviewer-Key`. Configure distinct high-entropy secrets; use HTTPS and a real identity-aware authorization system before production. The standalone Streamlit UI now **fails closed by default**: set `FLOWAGENT_ENABLE_LOCAL_UI=true` and configure `FLOWAGENT_REVIEWER_KEY` to allow local demo access. This is only a shared-key demo gate, **not** identity-aware authentication, and must not be exposed publicly. A configured but unavailable Postgres checkpointer fails closed instead of silently switching to volatile memory. Web research and LLM calls still need robust error handling and security review.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # add OPENAI_API_KEY (and TAVILY_API_KEY for real search)
set -a; source .env; set +a  # export credentials for this shell (trusted local file only)
```

### Run the API (two-step because it pauses for a human)
```bash
uvicorn app.main:app --reload
```

Start a verification:
```bash
curl -X POST http://localhost:8000/verify \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $FLOWAGENT_API_KEY" \
  -d '{"vendor_name":"Acme Supplies Inc.","submitted_docs":["Certificate of Insurance","GST/HST Registration"]}'
# -> returns { "thread_id": "...", "status": "awaiting_approval", "approval_request": {...} }
```

Approve (or reject) it:
```bash
curl -X POST http://localhost:8000/verify/resume \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $FLOWAGENT_API_KEY" \
  -H "X-Reviewer-Key: $FLOWAGENT_REVIEWER_KEY" \
  -d '{"thread_id":"PASTE_THREAD_ID","decision":"approve","comment":"Insurance verified."}'
# -> returns the final memo
```

### Run the UI
```bash
FLOWAGENT_ENABLE_LOCAL_UI=true streamlit run streamlit_app.py --server.address=127.0.0.1\n# Enter the FLOWAGENT_REVIEWER_KEY in the password field. Local demo only.
```

## Deployment
**No public backend is deployed or recommended for this portfolio prototype.** The Dockerfile supports private testing. Production would require user identity, reviewer roles, an audit log, concurrency-safe approvals, secure credentials and operational controls. A persistent Postgres checkpointer alone is not sufficient.

## Known limitations
- Document "checking" matches by name; it doesn't yet parse/validate the document contents.
- Single approval gate; no multi-level approval routing.
- Risk model is heuristic + LLM, not a trained scoring model.
- Web search quality depends on Tavily results.

## What I would improve next
- Parse uploaded documents (dates, coverage amounts, expiry) instead of name-matching.
- Add an OAuth-scoped tool layer / MCP server for the document and CRM systems.
- Multi-step approval routing (analyst → manager) with audit log.
- Retry/error-handler nodes for tool failures.
- Wire **GuardEval** to score task completion and decision consistency in CI.
