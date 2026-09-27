"""Streamlit frontend (D-013): run an event through the Phase 1 pipeline and explain the result.

Run:  streamlit run frontend/app.py          (LLM_BACKEND=stub for an offline demo)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pydantic import ValidationError  # noqa: E402

from frontend.view import (ROUTING, VERIFICATION, confidence_text, trust_text,  # noqa: E402
                           verdict_label)
from src.config import SystemConfig  # noqa: E402
from src.models import FinalRecommendation, SecurityEvent  # noqa: E402

st.set_page_config(page_title="Trust-aware cyber defense", page_icon="🛡️", layout="wide")


@st.cache_resource
def get_coordinator():
    from src.pipeline import build_coordinator
    return build_coordinator(SystemConfig.from_env())


def load_examples() -> dict[str, dict]:
    examples = {}
    for event in json.loads((ROOT / "data/events/demo_events.json").read_text()):
        examples[f"Demo: {event['metadata']['scenario']}"] = event
    eval_path = ROOT / "data/processed/eval_events.jsonl"
    if eval_path.exists():
        for line in eval_path.open().readlines()[:40]:
            event = json.loads(line)
            examples[f"UNSW-NB15 test record {event['metadata']['record_id']}"] = event
    return examples


def load_fixtures() -> dict[str, dict]:
    return {json.loads(p.read_text())["scenario"]: json.loads(p.read_text())
            for p in sorted((ROOT / "docs/frontend/fixtures").glob("scenario_*.json"))}


def render_result(event: SecurityEvent, result: FinalRecommendation) -> None:
    tags = [t for t, on in [("synthetic data", event.metadata.get("source") == "SYNTHETIC"),
                            ("mock / stub model", result.is_mock)] if on]
    st.caption(f"Event {result.event_id} · phase {result.phase} · run {result.run_id}"
               + (f" · {', '.join(tags)}" if tags else ""))

    icon, routing = ROUTING[result.routing]
    st.subheader(f"{verdict_label(result.verdict)} — {result.classification}")
    left, right = st.columns(2)
    left.markdown(f"**Confidence** {confidence_text(result.confidence, result.confidence_value)}")
    right.markdown(f"**Next step** {icon} {routing}")
    st.markdown(f"Why: {result.routing_reason}")
    if result.simulated_action:
        st.info(f"SIMULATED — nothing was executed. {result.simulated_action.description}")
    if result.disagreement_summary:
        st.warning(f"Agents disagree: {result.disagreement_summary}")

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
            st.caption(f"{finding.classification} · {confidence_text(finding.confidence)}"
                       + (f" · {finding.model}" if finding.model else ""))
            if finding.error:
                st.error(f"Agent failed: {finding.error}")
            if finding.evidence:
                st.code(finding.evidence, language=None)
            if finding.agent in status:
                v_icon, v_text = VERIFICATION[status[finding.agent].status]
                st.markdown(f"{v_icon} {v_text}")
                st.caption(status[finding.agent].reason)
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


st.title("Trust-aware cyber defense")
mode = st.sidebar.radio("Results from", ["Live pipeline", "Saved examples"],
                        help="Saved examples are mock fixtures used while the backend is unavailable.")

if mode == "Saved examples":
    fixtures = load_fixtures()
    choice = st.selectbox("Example", list(fixtures))
    data = fixtures[choice]
    render_result(SecurityEvent.model_validate(data["event"]), FinalRecommendation.model_validate(data["result"]))
else:
    config = SystemConfig.from_env()
    model_note = "stub model (offline, not Qwen)" if config.llm_backend == "stub" else f"{config.llm_model} at {config.llm_base_url}"
    st.sidebar.caption(f"Detection model: {model_note}")
    pick, paste = st.tabs(["Choose an event", "Paste event JSON"])
    with pick:
        examples = load_examples()
        name = st.selectbox("Event", list(examples))
        picked = examples[name]
    with paste:
        pasted = st.text_area("SecurityEvent JSON", height=180, placeholder='{"event_id": "...", ...}')
    use_pasted = bool(pasted.strip())
    if st.button("Analyze event", type="primary"):
        try:
            raw = json.loads(pasted) if use_pasted else picked
            event = SecurityEvent.model_validate(raw)
        except json.JSONDecodeError as error:
            st.error(f"That is not valid JSON: {error}")
        except ValidationError as error:
            st.error("The event does not match the SecurityEvent schema:")
            for item in error.errors():
                st.markdown(f"- `{'.'.join(map(str, item['loc']))}`: {item['msg']}")
        else:
            with st.spinner("Running Detection, Intelligence, Behavioral Analysis and Verification…"):
                result = get_coordinator().process_event(event)
            render_result(event, result)
    else:
        st.caption("Choose an event, or paste one, then select Analyze event.")
