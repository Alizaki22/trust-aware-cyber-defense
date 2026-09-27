# Input/Output Contract Proposal and Draft D-013

Owner: Member 3 (Frontend & Product) · Day 1, Phase 3 of 3 · Status: **REVIEWED BY M1 (DAY 2) — adopted into `docs/API_REFERENCE.md`; see "M1 Response" at the bottom of this file**

This document turns the frontend needs in `FRONTEND_SPEC.md` and the gaps in `DOC_REVIEW.md` (G-01 – G-10) into a concrete contract for M1 to review. **Nothing here changes `docs/API_REFERENCE.md` or `docs/DECISIONS.md`** until the team approves it and M1 records it.

- **Needed by:** Day 2 (M1 finalises schemas), so the Day 3 frontend components are built on the agreed shape.
- **Runnable reference:** every model below is implemented and validated in `fixtures/make_fixtures.py`.

## Part A — Input Contract (`SecurityEvent`)

These rules are enforced in the frontend (P1 Analyze) *and* in the backend. The backend is the authority; the frontend repeats the rules only to give early feedback (R-20).

| Field | Required | Type | Rule | UI error message |
|---|---|---|---|---|
| `event_id` | Yes | string | 1–64 chars | "Event ID is required" |
| `timestamp` | Yes | datetime | ISO 8601 (e.g. `2026-09-21T14:03:55Z`) | "Use ISO 8601, e.g. 2026-09-21T14:03:55Z" |
| `event_type` | Yes | string | non-empty; suggested values `log_entry`, `network_flow`, `email` | "Event type is required" |
| `raw_content` | Yes | string | 1 – 10,000 chars (**max is a placeholder**; confirm with M1/M2 for token cost) | "Raw content is required" / "Too long" |
| `source_ip` | No | IPv4/IPv6 | valid address if present | "Not a valid IP address" |
| `destination_ip` | No | IPv4/IPv6 | valid address if present | "Not a valid IP address" |
| `destination_port` | No | integer | 0–65535 | "Port must be 0–65535" |
| `protocol` | No | string | — | — |
| `entity` | No | string | user/host id for Behavioral Analysis | — |
| `metadata` | No | object | `metadata.source = "SYNTHETIC"` shows the SYNTHETIC tag (R-07) | "Must be a JSON object" |

Additional input rules:

- **Upload:** `.json` only, one event per file. Multi-event upload is out of scope for MVP.
- **Raw content is untrusted (R-08).** It is stored and displayed as plain text only. The frontend never interprets it as HTML or Markdown.
- `fixtures/invalid_event.json` is a deliberately broken event. It fails on 4 fields and is used to build and test the P1 error state.

**Change vs today:** `API_REFERENCE.md` already defines these fields. This proposal only adds the constraints: the IP type, the port range and the length limits.

## Part B — Output Contract Changes (`FinalRecommendation`)

### B1. Type the loose fields (G-08)

| Field | Today | Proposed |
|---|---|---|
| `agent` (all models) | `str` | `Literal["detection", "intelligence", "behavioral"]` |
| `confidence` | `str` | `Literal["high", "medium", "low", "none"]` |
| `VerificationResult.status` | `str` | `Literal["verified_consistent", "verified_inconsistent", "inconclusive"]` |
| `routing` | `str` | `Literal["simulated_action", "further_verification", "human_review"]` |
| `agent_findings` | `list` | `list[AgentFinding]` |
| `trust_scores` | `list` | `list[TrustScore]` |

**Why:** each of these values maps to a fixed visual state (FRONTEND_SPEC §6.2). A typo in a free string would silently break a card, and typed fields make Pydantic catch it at the source.

### B2. Additions to `AgentFinding`

| Field | Type | Gap | Why |
|---|---|---|---|
| `verdict` | `Literal["malicious", "suspicious", "benign", "unknown"]` | G-07 | The agents answer different questions (a classification, an IOC match, an anomaly). Peer agreement and a weighted vote both need **one comparable scale**; `classification` stays as the free, detailed label. `unknown` means abstain, e.g. "no match" or "no baseline" (R-02, R-03). |
| `error` | `Optional[str]` | G-09 | Separates "agent failed" (LLM/parse error) from "agent unsure". Both are currently `confidence: "none"`. Needed for the Partial state (R-18). |

G-10 also needs resolving: AGENT_DESIGN's `AgentFinding` should gain `event_id` to match API_REFERENCE.

### B3. Additions to `FinalRecommendation`

| Field | Type | Gap | Why / used by |
|---|---|---|---|
| `verification_results` | `list[VerificationResult]` | G-03 | Verification is computed but not returned; agent card badges need it (R-13) |
| `trust_weighted` | `WeightingOutcome` | G-04 | Trust Impact panel (R-16) |
| `equal_weighted` | `WeightingOutcome` | G-04 | Same panel; also the Experiment 2 control condition |
| `trust_changed_outcome` | `bool` | G-04 | ★ banner; easy to count during evaluation |
| `verdict` | `Verdict` | G-07 | Final verdict chip |
| `confidence_value` | `float` (0–1) | G-06 | `confidence_threshold` is a float, so routing needs a number; `confidence` becomes the label derived from it |
| `routing_reason` | `str` | — | "Why human review?" line on the final banner (R-15) |
| `simulated_action` | `Optional[SimulatedAction]` | — | Simulated action box. `executed: Literal[False]` makes D-011 part of the schema itself (R-01). |
| `run_id` | `str` | G-05 | Header; links P4 rows back to runs |
| `phase` | `Literal[1, 2]` | G-05 | Header; Phase Comparison (R-17) |
| `model` | `str` | G-05 | Header; names the model without assuming which agent is fine-tuned (D-010) |
| `created_at` | `datetime` | G-05 | Header; experiment logs |
| `is_mock` | `bool` | — | MOCK tag (R-07, R-23) |

New helper models:

```python
class WeightingOutcome(BaseModel):
    method: Literal["trust_weighted", "equal_weighted"]
    verdict: Verdict                    # "unknown" when tied or no votes
    verdict_weights: dict[str, float]   # verdict -> summed weight
    tie: bool = False

class SimulatedAction(BaseModel):
    description: str                    # "Would block 203.0.113.45 at ..."
    executed: Literal[False] = False    # can never be True (D-011)
```

**Unchanged:** `classification`, `confidence`, `disagreement_summary`, `reasoning`, `TrustScore` fields, `VerificationResult` fields (apart from the typing in B1).

### B4. Placeholder logic used in the fixtures — NOT decisions (G-13)

These placeholders exist only so the mock numbers are internally consistent. M1/M2 may accept, change or replace any of them. The UI **displays** whatever the backend returns and does not depend on these rules.

| Item | Placeholder | Source of default |
|---|---|---|
| Weights w1 / w2 / w3 | 0.40 / 0.35 / 0.25 | API_REFERENCE `SystemConfig` defaults |
| Verification score | consistent 1.0 · inconclusive 0.5 · inconsistent 0.0 | M3 placeholder |
| Peer agreement | Share of the *other* agents' historical accuracy that agrees with this verdict. It uses history rather than trust to avoid circularity. | M3 placeholder |
| Aggregation | Sum of trust per verdict; `unknown` or failed agents abstain; a tie means no winner (`unknown`) | M3 placeholder |
| `confidence_value` | Winning verdict's share of total weight; ≥ 0.75 high, ≥ 0.55 medium, else low | M3 placeholder |
| Threshold | 0.60 | API_REFERENCE `SystemConfig` default |
| Routing | `human_review` if value < 0.60 or agents disagree on a non-benign verdict; `further_verification` if benign; else `simulated_action` | M3 placeholder |

## Part C — Draft D-013: Frontend Technology (G-01, G-02)

To be copied into `docs/DECISIONS.md` by M1 once the team decides.

> ### D-013 — Frontend Technology
>
> **Decision:** TO BE DECIDED — M3 recommends Option 1.
>
> **Context:** D-007 defines no frontend technology, and ARCHITECTURE.md lists the output layer as "dashboard/report — TBD". The 10-day plan needs a frontend skeleton on Day 2, backend integration on Day 5 and a demo build on Day 10.
>
> | | Option 1: Streamlit | Option 2: React (Vite) + FastAPI |
> |---|---|---|
> | Languages | Python only | TypeScript + Python |
> | API layer | Not needed — imports the pipeline directly | Required — FastAPI moves from "only if required" to required |
> | Effort (10 days) | Low | ~2× (API, CORS, two build systems) |
> | Pages | Multipage via `pages/` | Full client routing |
> | Visual control | Enough for FRONTEND_SPEC (columns, expanders, charts) | Unlimited |
> | Who can maintain | All three members | Mainly M3 |
> | New dependencies | `streamlit` (+ optional `plotly`) | `react`, `vite`, a chart library, `fastapi`, `uvicorn` |
>
> **M3 recommendation:** Option 1. It follows D-006 (student-friendly, simple), keeps the stack Python-only, and removes the Day 5 API dependency (G-02). Option 2 is only worth it if the team wants web-app experience as an explicit learning objective.
>
> **Consequences if Option 1 is approved:** add `streamlit` to D-007; the frontend lives in `frontend/` and calls `Coordinator.process_event()` directly; FastAPI stays "only if required"; mock mode loads `docs/frontend/fixtures/`.
>
> **Status:** TO BE DECIDED

## Part D — Questions for M1

1. Can B1–B3 go into `src/models/` on Day 2–3, and should I open a PR updating `API_REFERENCE.md` once you agree?
2. Will the backend compute `equal_weighted` alongside `trust_weighted`? Preferred, so evaluation and UI use the same logic. Otherwise the frontend would compute it from the findings.
3. Is the `verdict` scale (B2) acceptable to M2 for prompts and fine-tuning labels?
4. D-013: can the team decide by the start of Day 2?
5. Trust history across runs (G-14): will it be persisted as JSONL? It is only needed for the stretch Trust History page.
6. Reports (G-15): which report is M3 responsible for?

---

## M1 Response (Day 2)

This is genuinely excellent work — thorough, correctly scoped (nothing here silently changed a decision), and it made Day 2 significantly faster. Answers to Part D, and what was adopted:

**Adopted into `docs/API_REFERENCE.md` as-is or with minor naming:** B1 (typed fields), B2 (`verdict` and `error` on `AgentFinding`), B3 in full (`verification_results`, `trust_weighted`, `equal_weighted`, `trust_changed_outcome`, `verdict`, `confidence_value`, `routing_reason`, `simulated_action`, `run_id`, `phase`, `model`, `created_at`, `is_mock`, plus the `WeightingOutcome` and `SimulatedAction` helper models). A `Verdict` type alias was added since the proposal referenced it without formally defining it. G-10 was also fixed while I was in there: `docs/AGENT_DESIGN.md`'s illustrative `AgentFinding` no longer redefines the schema — it now points to `API_REFERENCE.md` as the single source.

**Part A (input constraints):** adopted — `event_id` length, `raw_content` length (kept as a placeholder, flagged for revisit once a base model is chosen), IP typing, and port range are now in `SecurityEvent` in `API_REFERENCE.md`.

1. **Yes** — and since this PR already updates `API_REFERENCE.md` directly, a separate PR from you for B1–B3 isn't needed. `src/models/` implementation on Day 2–3 is still yours/M2's to build against this now-finalized schema.
2. **Yes** — `FinalRecommendation` returns both `trust_weighted` and `equal_weighted` always, not just the winner. Good catch; this was the right call for Experiment 2 and for keeping the UI from having to recompute aggregation logic.
3. **Accepted** — `Verdict = Literal["malicious", "suspicious", "benign", "unknown"]` is now canonical in `API_REFERENCE.md`. Flagging for M2: your Detection Agent prompts and any fine-tuning labels should target this same four-value scale so peer agreement/voting works across agents without a translation layer.
4. **D-013 decided:** Streamlit, per your Option 1 recommendation and reasoning — see `docs/DECISIONS.md`. This also resolves G-02: since Streamlit calls the Coordinator in-process, there's no Day 5 API-layer dependency; FastAPI stays "only if required."
5. **Yes** — JSONL, consistent with D-007's existing "JSON/JSONL for initial data storage" choice. Scoped as stretch (Trust History page), not required for MVP.
6. **Resolved (G-15)** — see the clarification added to D-008 in `docs/DECISIONS.md`: "Reports" under your scope means presentation/demo materials (slides, screenshots, demo script). The technical Phase 1 vs Phase 2 evaluation report is M2's output (`docs/EXPERIMENTS.md`); you present and visualize it.

**Also fixed while auditing (from your `DOC_REVIEW.md` list):** G-11 (`docs/architecture/AGENT_SPECIFICATION.md` said agent findings are visible to peer agents; `AGENT_DESIGN.md`/`DATA_FLOW.md` said agents run independently — resolved in favor of independent execution, matching the majority of the design and the Coordinator sequence diagram). G-12 (Verification is decided as rule-based Python in Phase 1, not LLM-based — updated `AGENT_DESIGN.md` and `THREAT_MODEL.md` accordingly). G-16 (removed the stale `docs/TRUST_MODEL.md` tree entry from `SYSTEM_ARCHITECTURE.md`). G-17 (placeholder clone URL, `requirements-dev.txt` reference, and hardcoded `gpt-3.5-turbo` in `DEVELOPMENT_GUIDE.md`).

**Not resolved, deliberately left open:**
- **G-18** (title vs. repo name mismatch) is a branding call for the whole team, not something to fix inside a docs PR by renaming the GitHub repo unilaterally.
- Numeric values inside the now-fixed schema shapes — trust weights, confidence threshold, initial trust score — remain **TO BE DECIDED**, same as before. This PR fixed the *shape* of the contract, not the numbers inside it.

Nice work — this made Day 2 land faster and cleaner than it would have otherwise.
