"""C2 leakage safety: reference data comes from the TRAIN split only; agents never read ground truth."""
import json

import pandas as pd
import pytest

from src.config import SystemConfig
from src.data.unsw_nb15 import (build_behavioral_profiles, build_intel_signatures, build_splits, load_events,
                                prepare)
from src.models import SecurityEvent
from src.pipeline import build_specialists
from tests.conftest import REAL_RAW, make_unsw_frame


def _raw_frames():
    train = make_unsw_frame(60, start_id=1, seed=1)
    test = make_unsw_frame(20, start_id=10_001, seed=2)
    return train, test


def _flip(df: pd.DataFrame, ids) -> pd.DataFrame:
    """Invert label / attack_cat of the given ids (a consistent but wrong labelling)."""
    df = df.copy()
    rows = df["id"].isin(ids)
    df.loc[rows, "label"] = 1 - df.loc[rows, "label"]
    df.loc[rows, "attack_cat"] = df.loc[rows, "label"].map({0: "Normal", 1: "Exploits"})
    return df


def test_reference_data_ignores_test_labels():
    train_raw, test_raw = _raw_frames()
    splits = build_splits(train_raw, test_raw)["splits"]
    baseline = (build_intel_signatures(splits["train"]), build_behavioral_profiles(splits["train"]))
    assert baseline[0]["signatures"], "fixture must produce signatures"
    flipped = build_splits(train_raw, _flip(test_raw, set(test_raw["id"])))["splits"]
    assert set(flipped["train"]["id"]) == set(splits["train"]["id"])
    assert (build_intel_signatures(flipped["train"]), build_behavioral_profiles(flipped["train"])) == baseline
    # ...while flipping TRAIN labels does change them (the check is sensitive).
    assert build_intel_signatures(_flip(splits["train"], set(splits["train"]["id"]))) != baseline[0]


def test_prepare_builds_reference_data_from_train_rows_only(data_dir, monkeypatch):
    """Records exactly which rows prepare() hands to the reference-data builders."""
    import src.data.unsw_nb15 as pipeline
    seen = {}
    for name in ("build_intel_signatures", "build_behavioral_profiles"):
        original = getattr(pipeline, name)
        def spy(df, _name=name, _original=original):
            seen[_name] = set(df["id"])
            return _original(df)
        monkeypatch.setattr(pipeline, name, spy)
    pipeline.prepare(data_dir, log=lambda *_: None)
    ids = {split: set(pd.read_csv(data_dir / "splits" / f"{split}.csv")["id"]) for split in ("train", "validation", "test")}
    for name, used in seen.items():
        assert used == ids["train"], name
        assert not used & ids["validation"] and not used & ids["test"], name


def test_prepare_writes_reference_data_built_from_train_split(data_dir):
    prepare(data_dir, log=lambda *_: None)
    train = pd.read_csv(data_dir / "splits" / "train.csv", keep_default_na=False)
    stored = json.loads((data_dir / "processed" / "intel_signatures.json").read_text())
    assert stored == json.loads(json.dumps(build_intel_signatures(train)))
    assert "train split" in stored["source"]
    total_support = sum(s["support"] for s in stored["signatures"].values())
    assert total_support <= len(train)


@pytest.mark.skipif(not (REAL_RAW / "UNSW_NB15_training-set.csv").exists(), reason="official UNSW-NB15 files not present")
def test_real_reference_data_is_train_only():
    root = REAL_RAW.parents[1]
    if not (root / "processed" / "intel_signatures.json").exists():
        pytest.skip("run `python -m src.cli prepare-data` first")
    train = pd.read_csv(root / "splits" / "train.csv", keep_default_na=False)
    stored = json.loads((root / "processed" / "intel_signatures.json").read_text())
    assert stored == json.loads(json.dumps(build_intel_signatures(train)))
    profiles = json.loads((root / "processed" / "behavioral_profiles.json").read_text())
    assert profiles == json.loads(json.dumps(build_behavioral_profiles(train)))


def test_agents_never_read_ground_truth(data_dir, tmp_path):
    prepare(data_dir, log=lambda *_: None)
    agents = build_specialists(SystemConfig(llm_backend="stub", data_dir=data_dir, runs_dir=tmp_path / "runs"))
    for path in ("eval_events.jsonl", "calibration_events.jsonl"):
        for raw in load_events(data_dir / "processed" / path):
            event = SecurityEvent.model_validate(raw)
            twin = event.model_copy(deep=True)
            twin.metadata["ground_truth"] = {"label": 1 - event.metadata["ground_truth"]["label"], "attack_cat": "X"}
            for agent in agents.values():
                assert agent.analyze(event).model_dump() == agent.analyze(twin).model_dump()
