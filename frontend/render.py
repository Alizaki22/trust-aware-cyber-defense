"""Result rendering (FRONTEND_SPEC P2). Model- and event-derived text is always
shown literally: escaped with ``plain`` or rendered with st.code / st.text (R-08)."""
from __future__ import annotations

import streamlit as st

from frontend.view import ROUTING, VERIFICATION, confidence_text, plain, trust_text, verdict_label
from src.models import FinalRecommendation, SecurityEvent


def render_result(event: SecurityEvent, result: FinalRecommendation) -> None:
    tags = [t for t, on in [("synthetic data", event.metadata.get("source") == "SYNTHETIC"),
                            ("mock / stub model", result.is_mock)] if on]
    st.caption(f"Event {result.event_id} · phase {result.phase} · run {result.run_id}"
               + (f" · {', '.join(tags)}" if tags else ""))

    icon, routing = ROUTING[result.routing]
    st.subheader(f"{verdict_label(result.verdict)} — {plain(result.classification)}")
    left, right = st.columns(2)
    left.markdown(f"**Confidence** {confidence_text(result.confidence, result.confidence_value)}")
    right.markdown(f"**Next step** {icon} {routing}")
    st.markdown(f"Why: {result.routing_reason}")
    if result.simulated_action:
        st.info(f"SIMULATED — nothing was executed. {plain(result.simulated_action.description)}")
    if result.disagreement_summary:
        st.warning(f"Agents disagree: {plain(result.disagreement_summary)}")

    st.markdown("#### Did trust change the outcome?")
    eq, tw = st.columns(2)
    for column, outcome, title in [(eq, result.equal_weighted, "Every agent counted equally"),
                                   (tw, result.trust_weighted, "Weighted by trust")]:
        column.markdown(f"**{title}:** {verdict_label(outcome.verdict)}" + (" (tie)" if outcome.tie else ""))
        for verdict, weight in sorted(outcome.verdict_weights.items()):
            column.progress(min(weight / max(sum(outcome.verdict_weights.values()), 1e-9), 1.0),
                            text=f"{verdict}: {weight:.2f}")
    if result.trust_changed_outcome:
        st.success("Trust weighting changed the outcome for this event.")
    else:
        st.caption("Both methods reached the same outcome.")

    st.markdown("#### What each agent found")
    status = {v.agent: v for v in result.verification_results}
    trust = {t.agent: t for t in result.trust_scores}
    for column, finding in zip(st.columns(len(result.agent_findings)), result.agent_findings):
        with column.container(border=True):
            st.markdown(f"**{finding.agent.capitalize()}**")
            st.markdown(verdict_label(finding.verdict, finding.classification))
            st.caption(f"{plain(finding.classification)} · {confidence_text(finding.confidence)}"
                       + (f" · {plain(finding.model)}" if finding.model else ""))
            if finding.error:
                st.error(f"Agent failed: {plain(finding.error)}")
            if finding.evidence:
                st.code(finding.evidence, language=None)
            if finding.agent in status:
                v_icon, v_text = VERIFICATION[status[finding.agent].status]
                st.markdown(f"{v_icon} {v_text}")
                st.caption(plain(status[finding.agent].reason))
            if finding.agent in trust:
                t = trust[finding.agent]
                st.markdown(f"Trust **{trust_text(t.total_score)}**",
                            help="A weighting heuristic, not a probability of being correct.")
                st.caption(f"history {t.historical_accuracy:.2f} · verification {t.verification_score:.2f}"
                           f" · peer agreement {t.peer_agreement:.2f}")
            with st.expander("Reasoning"):
                st.text(finding.reasoning)

    with st.expander("Raw event and result"):
        st.code(event.raw_content, language=None)  # untrusted content: plain text only
        st.json(result.model_dump(mode="json"), expanded=False)
