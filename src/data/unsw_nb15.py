"""UNSW-NB15 data pipeline (locked decision #1).

Single canonical implementation of Phase 1 data preparation:

  raw official CSVs (data/raw/unsw_nb15/, not committed)
    -> schema/label validation and cleaning
    -> dedup on the reduced Detection features (each official file)
    -> remove training records whose model input occurs in the test file
    -> stratified, input-group-aware train/validation split (seed 42)
    -> data/splits/{train,validation,test}.{csv,jsonl}   (fine-tuning format)
    -> data/processed/behavioral_profiles.json            (from TRAIN normals only)
    -> data/processed/intel_signatures.json               (from TRAIN only)
    -> frozen evaluation subset (test) + calibration subset (validation)

The methodology and output format are identical to the dataset-fix branch
(`fix/day2-dataset-leakage-and-schema`); see docs/PHASE1_IMPLEMENTATION.md §5.
"""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd

from src.agents.prompts import DETECTION_INSTRUCTION, INPUT_HEADER, format_detection_input
from src.models.types import ATTACK_CLASSES as _ATTACK_CLASSES
from src.models.types import DETECTION_CLASSES
from src.models.types import NORMAL_CLASS as _NORMAL_CLASS

RANDOM_STATE = 42
VALIDATION_FRACTION = 0.10

TRAIN_FILE_NAME = "UNSW_NB15_training-set.csv"
TEST_FILE_NAME = "UNSW_NB15_testing-set.csv"

REQUIRED_COLUMNS = [
    "id", "dur", "proto", "service", "state", "spkts", "dpkts", "sbytes", "dbytes",
    "rate", "sttl", "dttl", "sload", "dload", "sloss", "dloss", "sinpkt", "dinpkt",
    "sjit", "djit", "swin", "stcpb", "dtcpb", "dwin", "tcprtt", "synack", "ackdat",
    "smean", "dmean", "trans_depth", "response_body_len", "ct_srv_src", "ct_state_ttl",
    "ct_dst_ltm", "ct_src_dport_ltm", "ct_dst_sport_ltm", "ct_dst_src_ltm",
    "is_ftp_login", "ct_ftp_cmd", "ct_flw_http_mthd", "ct_src_ltm", "ct_srv_dst",
    "is_sm_ips_ports", "attack_cat", "label",
]

# The 14 raw features shown to the Detection model (unscaled, human-readable).
DETECTION_FEATURES = [
    "dur", "proto", "service", "state", "spkts", "dpkts", "sbytes", "dbytes",
    "rate", "sttl", "dttl", "sload", "dload", "tcprtt",
]
CATEGORICAL_FEATURES = ["proto", "service", "state"]
TARGET_FIELDS = {"label", "attack_cat"}
DEDUP_SUBSET = DETECTION_FEATURES + ["attack_cat", "label"]

# Label vocabulary: the canonical DETECTION_CLASSES (src/models/types.py),
# shared with the Detection prompt, output schema, Verification and metrics.
NORMAL_CLASS = _NORMAL_CLASS
ATTACK_CATEGORIES = list(_ATTACK_CLASSES)
CLASSIFICATIONS = list(DETECTION_CLASSES)
LABEL_TO_VERDICT = {0: "benign", 1: "malicious"}
OUTPUT_FIELDS = ["verdict", "classification", "evidence", "confidence", "reasoning"]
TRAINING_CONFIDENCE = "high"  # placeholder: labels carry no confidence information
EVIDENCE_FEATURES = ["proto", "service", "state", "spkts", "dpkts", "sbytes", "dbytes", "sttl", "dttl"]

# Behavioral profile baseline (built from TRAIN-split Normal records only)
PROFILE_NUMERIC_FEATURES = ["dur", "spkts", "dpkts", "sbytes", "dbytes", "rate", "sload", "dload", "tcprtt"]
PROFILE_SET_FEATURES = ["state", "sttl", "dttl"]
PROFILE_MIN_RECORDS = 30
PROFILE_QUANTILES = (0.01, 0.99)

# Intelligence flow-signature reputation (built from the TRAIN split only).
# A signature is the exact (proto, service, state, sttl, dttl) tuple. It is
# "known malicious" / "known benign" only with enough support and a clear
# majority; everything else is "no match" (an abstention, never benign).
SIGNATURE_FEATURES = ["proto", "service", "state", "sttl", "dttl"]
SIGNATURE_MIN_SUPPORT = 20
SIGNATURE_MALICIOUS_SHARE = 0.95   # attack share >= this -> known malicious
SIGNATURE_BENIGN_SHARE = 0.05      # attack share <= this -> known benign

# Frozen subsets (stratified by class, seeded)
EVAL_PER_CLASS = 50          # from the official test split  -> ~494 events
CALIBRATION_PER_CLASS = 20   # from the validation split     -> ~192 events

# Timestamps are not part of the UNSW-NB15 partition files.
PLACEHOLDER_TIMESTAMP = "1970-01-01T00:00:00Z"


# ---------------------------------------------------------------- load/clean
def load_raw(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {path}\nDownload the official UNSW-NB15 partition files "
            "(see data/raw/unsw_nb15/README.md).")
    if path.stat().st_size == 0:
        raise ValueError(f"Dataset is empty: {path}")
    df = pd.read_csv(path)
    df.columns = [str(column).strip().lstrip("\ufeff") for column in df.columns]
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"{path.name}: missing required columns {missing}")
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(how="all").copy()
    for column in CATEGORICAL_FEATURES + ["attack_cat"]:
        df[column] = df[column].astype(str).str.strip()
    df["label"] = pd.to_numeric(df["label"], errors="coerce")
    df = df.dropna(subset=["label"])
    df["label"] = df["label"].astype(int)
    if not df["label"].isin([0, 1]).all():
        raise ValueError("label must be binary 0/1")
    missing_features = df[DETECTION_FEATURES].isna().any(axis=1)
    if missing_features.any():  # none in the official files; kept explicit
        df = df.loc[~missing_features]
    inconsistent = (df["label"] == 0) != (df["attack_cat"] == NORMAL_CLASS)
    if inconsistent.any():
        raise ValueError(f"{int(inconsistent.sum())} records with label/attack_cat mismatch")
    unknown = ~df["attack_cat"].isin(CLASSIFICATIONS)
    if unknown.any():
        raise ValueError(f"unknown attack_cat values: {sorted(df.loc[unknown, 'attack_cat'].unique())}")
    return df.reset_index(drop=True)


# ---------------------------------------------------------------- formatting
def format_raw_content(row) -> str:
    """The 14 features as 'name=value, ...' (the Detection input body)."""
    return ", ".join(f"{column}={row[column]}" for column in DETECTION_FEATURES)


def create_detection_input(row) -> str:
    return format_detection_input(format_raw_content(row))


def create_evidence(row) -> str:
    return ", ".join(f"{column}={row[column]}" for column in EVIDENCE_FEATURES)


def create_detection_output(row) -> dict:
    label = int(row["label"])
    if label == 0:
        classification = NORMAL_CLASS
        reasoning = ("The cited protocol, connection state, packet/byte volumes and "
                     "TTL values are consistent with normal network traffic.")
    else:
        classification = str(row["attack_cat"])
        reasoning = ("The cited protocol, connection state, packet/byte volumes and "
                     f"TTL values match the {classification} attack category.")
    return {"verdict": LABEL_TO_VERDICT[label], "classification": classification,
            "evidence": create_evidence(row), "confidence": TRAINING_CONFIDENCE,
            "reasoning": reasoning}


def create_instruction_example(row) -> dict:
    return {"instruction": DETECTION_INSTRUCTION, "input": create_detection_input(row),
            "output": json.dumps(create_detection_output(row), ensure_ascii=False)}


# ---------------------------------------------------------------- splitting
def deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop_duplicates(subset=DEDUP_SUBSET, keep="first").reset_index(drop=True)


def add_input_key(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["_input"] = df.apply(create_detection_input, axis=1)
    return df


def remove_test_overlap(pool: pd.DataFrame, test: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    overlap = pool["_input"].isin(set(test["_input"]))
    return pool.loc[~overlap].reset_index(drop=True), int(overlap.sum())


def _group_stratum(categories: pd.Series) -> str:
    counts = categories.value_counts()
    return sorted(counts[counts == counts.max()].index)[0]


def stratified_group_split(pool: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    strata = pool.groupby("_input", sort=True)["attack_cat"].apply(_group_stratum)
    rng = random.Random(RANDOM_STATE)
    validation_inputs: set = set()
    for stratum in sorted(strata.unique()):
        keys = sorted(strata.index[strata == stratum])
        rng.shuffle(keys)
        n_validation = round(len(keys) * VALIDATION_FRACTION)
        if len(keys) >= 2:
            n_validation = max(1, min(n_validation, len(keys) - 1))
        validation_inputs.update(keys[:n_validation])
    in_validation = pool["_input"].isin(validation_inputs)
    return (pool.loc[~in_validation].reset_index(drop=True),
            pool.loc[in_validation].reset_index(drop=True))


def build_splits(train_raw: pd.DataFrame, test_raw: pd.DataFrame) -> dict:
    test = add_input_key(deduplicate(clean(test_raw)))
    pool = add_input_key(deduplicate(clean(train_raw)))
    pool, removed = remove_test_overlap(pool, test)
    train, validation = stratified_group_split(pool)
    splits = {"train": train, "validation": validation, "test": test}
    for a, b in [("train", "validation"), ("train", "test"), ("validation", "test")]:
        shared = set(splits[a]["_input"]) & set(splits[b]["_input"])
        if shared:
            raise AssertionError(f"{len(shared)} model inputs shared by {a} and {b}")
    return {"splits": {name: df.drop(columns="_input") for name, df in splits.items()},
            "removed_test_overlap": removed}


# ---------------------------------------------------------------- derived artifacts
def build_behavioral_profiles(train: pd.DataFrame) -> dict:
    """Per-(proto, service) normal-traffic profile from TRAIN-split Normal records."""
    normal = train.loc[train["label"] == 0]
    profiles = {}
    for (proto, service), group in normal.groupby(["proto", "service"], sort=True):
        if len(group) < PROFILE_MIN_RECORDS:
            continue
        low, high = PROFILE_QUANTILES
        profiles[f"{proto}|{service}"] = {
            "n": int(len(group)),
            "numeric": {f: [float(group[f].quantile(low)), float(group[f].quantile(high))]
                        for f in PROFILE_NUMERIC_FEATURES},
            "sets": {f: sorted(str(v) for v in group[f].unique()) for f in PROFILE_SET_FEATURES},
        }
    return {"source": "UNSW-NB15 train split, label=0 records only",
            "quantiles": list(PROFILE_QUANTILES), "min_records": PROFILE_MIN_RECORDS,
            "profiles": profiles}


def signature_key(values: dict) -> str:
    """'proto|service|state|sttl|dttl' with numbers normalised (254.0 -> 254)."""
    parts = []
    for feature in SIGNATURE_FEATURES:
        value = str(values[feature]).strip()
        try:
            number = float(value)
            value = str(int(number)) if number.is_integer() else str(number)
        except ValueError:
            pass
        parts.append(value)
    return "|".join(parts)


def build_intel_signatures(train: pd.DataFrame) -> dict:
    """Flow-signature reputation learned from TRAIN-split labels only."""
    keys = train.apply(lambda row: signature_key(row), axis=1)
    grouped = train.assign(_key=keys).groupby("_key", sort=True)
    signatures = {}
    for key, group in grouped:
        support = len(group)
        if support < SIGNATURE_MIN_SUPPORT:
            continue
        share = float(group["label"].mean())
        if share >= SIGNATURE_MALICIOUS_SHARE:
            reputation = "malicious"
        elif share <= SIGNATURE_BENIGN_SHARE:
            reputation = "benign"
        else:
            continue
        top = group.loc[group["label"] == 1, "attack_cat"].value_counts()
        signatures[key] = {"reputation": reputation, "support": support,
                           "attack_share": round(share, 4),
                           "top_attack_cat": str(top.index[0]) if len(top) else None}
    return {"source": "UNSW-NB15 train split flow-signature reputation (labels from train only)",
            "features": SIGNATURE_FEATURES, "min_support": SIGNATURE_MIN_SUPPORT,
            "malicious_share": SIGNATURE_MALICIOUS_SHARE, "benign_share": SIGNATURE_BENIGN_SHARE,
            "signatures": signatures}


def stratified_sample_ids(df: pd.DataFrame, per_class: int) -> list[int]:
    rng = random.Random(RANDOM_STATE)
    chosen: list[int] = []
    for category in CLASSIFICATIONS:
        ids = sorted(int(i) for i in df.loc[df["attack_cat"] == category, "id"])
        rng.shuffle(ids)
        chosen.extend(ids[:per_class])
    return sorted(chosen)


def to_security_event(row, split: str) -> dict:
    """UNSW-NB15 record -> SecurityEvent dict. Ground truth kept in metadata for evaluation."""
    return {
        "event_id": f"unsw-{split}-{int(row['id'])}",
        "timestamp": PLACEHOLDER_TIMESTAMP,
        "event_type": "network_flow",
        "protocol": str(row["proto"]),
        "raw_content": format_raw_content(row),
        "metadata": {
            "source": "UNSW-NB15", "split": split, "record_id": int(row["id"]),
            "timestamp_note": "not provided by the UNSW-NB15 partition files",
            "ground_truth": {"label": int(row["label"]), "attack_cat": str(row["attack_cat"])},
        },
    }


# ---------------------------------------------------------------- validation
def _parse_pairs(text: str) -> list[tuple[str, str]]:
    pairs = []
    for part in text.split(", "):
        if "=" not in part:
            raise ValueError(part)
        name, value = part.split("=", 1)
        pairs.append((name, value))
    return pairs


def check_training_record(record: dict) -> list[str]:
    if set(record) != {"instruction", "input", "output"} or not all(isinstance(record[k], str) for k in record):
        return ["record must have string instruction/input/output only"]
    errors = []
    if record["instruction"] != DETECTION_INSTRUCTION:
        errors.append("instruction differs from DETECTION_INSTRUCTION")
    header, _, body = record["input"].partition("\n")
    if header != INPUT_HEADER:
        errors.append("input header differs from INPUT_HEADER")
    try:
        input_pairs = _parse_pairs(body)
    except ValueError:
        return errors + ["input is not a feature=value list"]
    if [name for name, _ in input_pairs] != DETECTION_FEATURES:
        errors.append("input feature names/order differ from DETECTION_FEATURES")
    try:
        output = json.loads(record["output"])
    except json.JSONDecodeError:
        return errors + ["output is not valid JSON"]
    if not isinstance(output, dict) or set(output) != set(OUTPUT_FIELDS):
        return errors + ["output keys differ from the canonical finding fields"]
    if output["classification"] not in CLASSIFICATIONS:
        errors.append("unknown classification")
    elif output["verdict"] != LABEL_TO_VERDICT[0 if output["classification"] == NORMAL_CLASS else 1]:
        errors.append("verdict inconsistent with classification")
    if output["confidence"] not in {"high", "medium", "low", "none"}:
        errors.append("invalid confidence")
    try:
        if not set(_parse_pairs(output["evidence"])) <= set(input_pairs):
            errors.append("evidence cites values not present in the input")
    except ValueError:
        errors.append("evidence is not a feature=value list")
    return errors


def validate_split_files(splits_dir: Path, log=print) -> bool:
    ok, inputs = True, {}
    for name in ("train", "validation", "test"):
        path = splits_dir / f"{name}.jsonl"
        if not path.exists():
            log(f"FAIL {name}: missing {path}")
            ok = False
            inputs[name] = set()
            continue
        seen, n, bad, dup = set(), 0, 0, 0
        for line in path.open(encoding="utf-8"):
            n += 1
            if line in seen:
                dup += 1
            seen.add(line)
            try:
                errors = check_training_record(json.loads(line))
            except json.JSONDecodeError:
                errors = ["invalid JSON line"]
            if errors:
                bad += 1
                if bad <= 3:
                    log(f"  {name} line {n}: {errors}")
        inputs[name] = {json.loads(line)["input"] for line in seen if line.strip()}
        passed = n > 0 and bad == 0 and dup == 0
        log(f"{'PASS' if passed else 'FAIL'} {name}: {n} records, {bad} invalid, {dup} duplicate"
            + (" (EMPTY)" if n == 0 else ""))
        ok = ok and passed
    for a, b in [("train", "validation"), ("train", "test"), ("validation", "test")]:
        shared = len(inputs[a] & inputs[b])
        log(f"{'PASS' if not shared else 'FAIL'} {a} ∩ {b}: {shared} shared inputs")
        ok = ok and not shared
    return ok


# ---------------------------------------------------------------- orchestration
def _write_jsonl(path: Path, records: Iterable[dict]) -> int:
    count = 0
    with path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    return count


def _freeze_ids(path: Path, ids: list[int], description: str, log) -> list[int]:
    """Write the id list on first run; afterwards verify it has not drifted."""
    if path.exists():
        frozen = json.loads(path.read_text())["ids"]
        if frozen != ids:
            raise AssertionError(f"{path} differs from the regenerated subset -- data or code changed")
        log(f"verified frozen subset {path.name} ({len(ids)} ids)")
        return frozen
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"description": description, "seed": RANDOM_STATE, "ids": ids}, indent=0))
    log(f"froze {path.name} ({len(ids)} ids)")
    return ids


def prepare(data_dir: Path, log=print) -> dict:
    raw_dir = data_dir / "raw" / "unsw_nb15"
    splits_dir, processed_dir, eval_dir = data_dir / "splits", data_dir / "processed", data_dir / "eval"
    for directory in (splits_dir, processed_dir):
        directory.mkdir(parents=True, exist_ok=True)

    train_raw, test_raw = load_raw(raw_dir / TRAIN_FILE_NAME), load_raw(raw_dir / TEST_FILE_NAME)
    log(f"raw rows: train file {len(train_raw)}, test file {len(test_raw)}")
    built = build_splits(train_raw, test_raw)
    splits = built["splits"]
    log(f"removed {built['removed_test_overlap']} training records whose input occurs in test")

    summary = {"raw_rows": {"train_file": len(train_raw), "test_file": len(test_raw)},
               "removed_test_overlap": built["removed_test_overlap"], "splits": {}}
    for name, df in splits.items():
        df.to_csv(splits_dir / f"{name}.csv", index=False)
        _write_jsonl(splits_dir / f"{name}.jsonl", (create_instruction_example(row) for _, row in df.iterrows()))
        summary["splits"][name] = {"records": len(df),
                                   "classes": {c: int((df["attack_cat"] == c).sum()) for c in CLASSIFICATIONS}}
        log(f"{name}: {len(df)} records")

    profiles = build_behavioral_profiles(splits["train"])
    (processed_dir / "behavioral_profiles.json").write_text(json.dumps(profiles, indent=1))
    log(f"behavioral profiles: {len(profiles['profiles'])} (proto|service) profiles")

    signatures = build_intel_signatures(splits["train"])
    (processed_dir / "intel_signatures.json").write_text(json.dumps(signatures, indent=1))
    reputations = [v["reputation"] for v in signatures["signatures"].values()]
    log(f"intel signatures: {reputations.count('malicious')} known-malicious, "
        f"{reputations.count('benign')} known-benign")

    eval_ids = _freeze_ids(eval_dir / "phase1_eval_subset_ids.json",
                           stratified_sample_ids(splits["test"], EVAL_PER_CLASS),
                           f"Official test split, up to {EVAL_PER_CLASS} records per class", log)
    calibration_ids = _freeze_ids(eval_dir / "phase1_calibration_ids.json",
                                  stratified_sample_ids(splits["validation"], CALIBRATION_PER_CLASS),
                                  f"Validation split, up to {CALIBRATION_PER_CLASS} records per class", log)
    for name, split, ids in [("eval_events", "test", eval_ids), ("calibration_events", "validation", calibration_ids)]:
        df = splits[split].set_index("id").loc[ids].reset_index()
        count = _write_jsonl(processed_dir / f"{name}.jsonl", (to_security_event(row, split) for _, row in df.iterrows()))
        summary[name] = count
    (processed_dir / "prepare_summary.json").write_text(json.dumps(summary, indent=1))
    return summary


def load_events(path: Path, limit: Optional[int] = None) -> list[dict]:
    events = []
    with path.open(encoding="utf-8") as file:
        for line in file:
            events.append(json.loads(line))
            if limit is not None and len(events) >= limit:
                break
    return events
