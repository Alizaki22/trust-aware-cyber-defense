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

from frontend.render import render_result  # noqa: E402
from frontend.view import plain  # noqa: E402
from src.config import SystemConfig  # noqa: E402
from src.models import FinalRecommendation, SecurityEvent  # noqa: E402

st.set_page_config(page_title="Trust-aware cyber defense", page_icon="🛡️", layout="wide")


@st.cache_resource
def _coordinator_for(config_json: str):
    """One coordinator per configuration (a changed config never reuses a stale one)."""
    from src.pipeline import build_coordinator
    return build_coordinator(SystemConfig.model_validate_json(config_json))


def get_coordinator():
    return _coordinator_for(SystemConfig.from_env().model_dump_json())


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
    history = get_coordinator().trust.history
    if history.accuracy:
        st.sidebar.caption(f"Trust history: measured on the calibration subset ({plain(history.source)})")
    else:
        st.sidebar.warning("Trust history: not calibrated — every agent uses the initial trust score. "
                           "Run `python -m src.cli calibrate` for meaningful trust weights.")
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
            st.error(f"That is not valid JSON: {plain(error)}")
        except ValidationError as error:
            st.error("The event does not match the SecurityEvent schema:")
            for item in error.errors():
                st.markdown(f"- `{'.'.join(map(str, item['loc']))}`: {plain(item['msg'])}")
        else:
            with st.spinner("Running Detection, Intelligence, Behavioral Analysis and Verification…"):
                result = get_coordinator().process_event(event)
            render_result(event, result)
    else:
        st.caption("Choose an event, or paste one, then select Analyze event.")
