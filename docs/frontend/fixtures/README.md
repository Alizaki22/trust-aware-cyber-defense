# Frontend Mock Fixtures

**All data here is SYNTHETIC and MOCK.** These files are not model outputs or experiment results. They exist so the frontend can be built and demoed before the real pipeline exists (R-23).

| File | Scenario | Demonstrates | Final verdict | Equal-weighted | Routing |
|---|---|---|---|---|---|
| `scenario_01.json` | SSH brute force | All agents agree, evidence verified | malicious | malicious | simulated_action |
| `scenario_02.json` | Large upload from a finance laptop | Misleading Detection agent; trust weighting flips the outcome | malicious | benign | human_review |
| `scenario_03.json` | VPN login from a new country | Disagreement, Intelligence "no match", equal-weighted tie | suspicious | unknown (tie) | human_review |
| `invalid_event.json` | — | Input validation errors (4 bad fields) for the P1 error state | — | — | — |

Each scenario file is an `AnalysisRun`: `{ "scenario", "event": SecurityEvent, "result": FinalRecommendation }`, using the proposed schema in `../SCHEMA_PROPOSAL.md`.

Note on scenario 03: `trust_changed_outcome` is `true` because equal weighting tied (1 vs 1) and trust weighting broke the tie. Scenario 02 is the main "trust flips the outcome" demo.

## Regenerate and validate

```bash
pip install pydantic
python docs/frontend/fixtures/make_fixtures.py
```

The script:

1. checks that `invalid_event.json` is rejected
2. builds the three scenarios
3. validates them against the schema
4. rewrites the JSON files

Trust weights, thresholds, peer agreement and routing rules in the script are **placeholders**, not decisions (see `SCHEMA_PROPOSAL.md` Part B4). If the team changes them, update the script and regenerate; don't edit the JSON by hand.
