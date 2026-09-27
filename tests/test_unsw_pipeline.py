import json

import pytest

from src.data.unsw_nb15 import (DETECTION_FEATURES, check_training_record, prepare, validate_split_files)
from tests.conftest import REAL_RAW


def test_prepare_on_synthetic_data(data_dir):
    summary = prepare(data_dir, log=lambda *_: None)
    splits = data_dir / "splits"
    assert validate_split_files(splits, log=lambda *_: None)
    assert summary["removed_test_overlap"] >= 3  # the planted overlapping records
    records = [json.loads(l) for l in (splits / "train.jsonl").open()]
    assert all(check_training_record(r) == [] for r in records)
    assert all("label=" not in r["input"] and "attack_cat" not in r["input"] for r in records)
    profiles = json.loads((data_dir / "processed/behavioral_profiles.json").read_text())
    assert profiles["profiles"] and "train split, label=0" in profiles["source"]
    events = [json.loads(l) for l in (data_dir / "processed/eval_events.jsonl").open()]
    assert {e["metadata"]["split"] for e in events} == {"test"}
    assert len({e["metadata"]["ground_truth"]["attack_cat"] for e in events}) == 10


def test_prepare_is_deterministic_and_detects_subset_drift(data_dir):
    prepare(data_dir, log=lambda *_: None)
    first = (data_dir / "splits/train.jsonl").read_bytes()
    prepare(data_dir, log=lambda *_: None)  # verifies frozen ids instead of rewriting
    assert (data_dir / "splits/train.jsonl").read_bytes() == first
    ids_file = data_dir / "eval/phase1_eval_subset_ids.json"
    frozen = json.loads(ids_file.read_text())
    frozen["ids"] = frozen["ids"][:-1]
    ids_file.write_text(json.dumps(frozen))
    with pytest.raises(AssertionError):
        prepare(data_dir, log=lambda *_: None)


def test_validator_catches_leakage_and_empty_splits(data_dir):
    prepare(data_dir, log=lambda *_: None)
    splits = data_dir / "splits"
    test_line = (splits / "test.jsonl").open().readline()
    with (splits / "train.jsonl").open("a") as file:
        file.write(test_line)
    assert not validate_split_files(splits, log=lambda *_: None)
    prepare_dir = data_dir
    prepare(prepare_dir, log=lambda *_: None)
    (splits / "validation.jsonl").write_text("")
    assert not validate_split_files(splits, log=lambda *_: None)


def test_record_checks():
    good_input = "Analyze this network security event:\n" + ", ".join(f"{f}=1" for f in DETECTION_FEATURES)
    from src.agents.prompts import DETECTION_INSTRUCTION
    record = {"instruction": DETECTION_INSTRUCTION, "input": good_input,
              "output": json.dumps({"verdict": "benign", "classification": "Normal", "evidence": "dur=1",
                                    "confidence": "high", "reasoning": "r"})}
    assert check_training_record(record) == []
    swapped = {**record, "input": good_input.replace("dur=1, proto=1", "proto=1, dur=1")}
    assert "input feature names/order differ from DETECTION_FEATURES" in check_training_record(swapped)
    leaked = {**record, "input": good_input + ", label=0"}
    assert check_training_record(leaked)
    lying = {**record, "output": record["output"].replace("dur=1", "dur=9")}
    assert "evidence cites values not present in the input" in check_training_record(lying)


@pytest.mark.skipif(not (REAL_RAW / "UNSW_NB15_training-set.csv").exists(), reason="official UNSW-NB15 files not present")
def test_real_unsw_counts(tmp_path):
    import shutil
    d = tmp_path / "data"
    shutil.copytree(REAL_RAW, d / "raw" / "unsw_nb15")
    summary = prepare(d, log=lambda *_: None)
    assert {k: v["records"] for k, v in summary["splits"].items()} == {"train": 76621, "validation": 8525, "test": 45782}
    assert summary["raw_rows"] == {"train_file": 175341, "test_file": 82332}
    assert summary["removed_test_overlap"] == 2730
    assert validate_split_files(d / "splits", log=lambda *_: None)
