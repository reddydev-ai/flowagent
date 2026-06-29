"""Streamlit approval UI for FlowAgent.
Start a verification, review the agent's risk assessment, then approve/reject.
Run with:  streamlit run streamlit_app.py
"""
import uuid
import streamlit as st
from langgraph.types import Command

from app.config import get_settings
from app.graph import build_graph

settings = get_settings()

st.set_page_config(page_title="FlowAgent", page_icon="🛡️", layout="centered")
st.title("🛡️ FlowAgent — Vendor Verification")
st.caption("Agentic workflow: research → document check → risk decision → human approval → memo")

if "graph" not in st.session_state:
    st.session_state.graph = build_graph()
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "pending" not in st.session_state:
    st.session_state.pending = None

graph = st.session_state.graph

with st.form("start"):
    vendor = st.text_input("Vendor name", "Acme Supplies Inc.")
    docs = st.text_area("Submitted documents (one per line)",
                        "Certificate of Insurance\nGST/HST Registration")
    submitted = st.form_submit_button("Run verification")

if submitted:
    tid = str(uuid.uuid4())
    st.session_state.thread_id = tid
    cfg = {"configurable": {"thread_id": tid}}
    with st.spinner("Agent researching and assessing risk..."):
        graph.invoke(
            {"vendor_name": vendor,
             "submitted_docs": [d for d in docs.splitlines() if d.strip()]},
            config=cfg,
        )
    # Read the pending interrupt payload from graph state (not from invoke result).
    snap = graph.get_state(cfg)
    if snap.next and snap.tasks and snap.tasks[0].interrupts:
        st.session_state.pending = snap.tasks[0].interrupts[0].value
    else:
        st.session_state.pending = None

if st.session_state.pending is not None:
    req = st.session_state.pending
    st.subheader("Review")
    color = {"green": "🟢", "yellow": "🟡", "red": "🔴"}.get(req.get("risk_level"), "⚪")
    st.markdown(f"**Risk:** {color} {req.get('risk_level')}")
    st.markdown(f"**Rationale:** {req.get('risk_rationale')}")
    st.markdown(f"**Missing documents:** {req.get('missing_docs') or 'none'}")

    comment = st.text_input("Reviewer comment", "")
    c1, c2 = st.columns(2)
    decision = None
    if c1.button("✅ Approve"):
        decision = "approve"
    if c2.button("❌ Reject"):
        decision = "reject"

    if decision:
        cfg = {"configurable": {"thread_id": st.session_state.thread_id}}
        with st.spinner("Writing memo..."):
            final = graph.invoke(Command(resume={"decision": decision, "comment": comment}), config=cfg)
        st.session_state.pending = None
        st.success(f"Decision recorded: {decision}")
        st.markdown("### Final memo")
        st.markdown(final.get("memo", ""))
