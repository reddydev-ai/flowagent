# FlowAgent — AI Automation Product Case Study

**Project type:** Independent portfolio prototype · **Audience:** AI Automation Product Manager interview panel · **Evidence boundary:** No employer or customer business results are claimed.

## Problem and product decision
Vendor onboarding often includes document completeness checks, public-information review and an accountable human decision. FlowAgent explores where an agent can prepare work *without* being the final decision maker.

**Core principle:** High-impact vendor approval stays with an authenticated human reviewer. An LLM may propose or explain risk, but a deterministic document-based risk floor cannot be downgraded by generated text.

## Stakeholders and workflows

| Persona | Decision / need | MVP capability |
| --- | --- | --- |
| Onboarding operations | Collect complete supplier packet | Check required document names |
| Risk/compliance reviewer | Approve or reject | Explicit interrupt / separate reviewer key |
| Business owner | Understand exceptions | Risk and missing-document summary |
| Platform engineer | Recover state reliably | Checkpointing, tests, fail-closed persistence |

## Mini-PRD
**Trigger:** Vendor packet submitted.

**Workflow:** Authenticated submission → public information lookup (optional) → deterministic missing-document inspection → AI-assisted risk commentary if configured → mandatory human approval → outcome memo.

**Acceptance criteria:**
- Missing-document count must yield a deterministic minimum risk.
- Workflow must pause and expose the reviewer request.
- Submission credential alone must not authorize the reviewer.
- An already completed approval must not be applied twice.
- If explicitly configured persistent storage is unavailable, processing must fail instead of silently downgrading to volatile memory.

**Not in scope:** trusted identity directory, audit logging, asynchronous SLA management, fraud adjudication, legal advice, unattended approval, enterprise security certification.

## Product measurement plan

| Metric | Definition | Current status |
| --- | --- | --- |
| Human-approval integrity | Decision unchanged from authorized reviewer input | Synthetic integration tests only |
| Replay rejection | Repeat approvals rejected / repeat approval attempts | Synthetic integration tests only |
| Completeness accuracy | Correct missing-document sets / independently reviewed packets | Synthetic integration tests only |
| Escalation accuracy | High-risk cases sent to appropriate review tier | Needs business-policy labeling |
| Onboarding cycle time | Median elapsed business hours from submission to approval | Not measured |
| Manual effort saved | Analyst minutes saved per successfully reviewed vendor | Not measured |
| False-negative compliance risk | Non-compliant packets incorrectly approved / all non-compliant packets | Not measured |

## Build-vs-buy and risks
A rule engine is more transparent than an LLM for checking explicit document completeness; the agent is useful when it makes summaries and orchestrates reviews. Do not replace mandatory human approval with generated confidence scores. A shared reviewer key is suitable only for isolated demos—not enterprise RBAC.

## Three-step product roadmap
1. **Current:** controlled demonstration of deterministic risk, approvals and CI validation.
2. **Next:** proper identity-aware review, durable audit events, idempotency and concurrency testing; structured review queues.
3. **Later:** user studies, integration with procurement and ticketing systems, real business KPIs and secure deployment.

## Interview walkthrough
Show two synthetic vendors: one complete packet and one high-risk packet. Demonstrate a reviewer rejection, a wrong reviewer key, a replay attempt and the CI assertions. Contrast observable system outcomes with unverified business benefits.

## Evidence links
- [Implementation and deployment cautions](../README.md)
- [Real API integration tests](../tests/test_api_integration.py)
- [Security workflow](../.github/workflows/security.yml)
- [GuardEval service-level integration](https://github.com/reddydev-ai/guardeval/actions/workflows/live-integration.yml)

**Status:** Evaluated workflow prototype, no real-world adoption or vendor outcomes claimed.
