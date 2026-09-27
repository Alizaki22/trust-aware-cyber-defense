import json
import shutil
from pathlib import Path

import pandas as pd
import pytest

from src.config import SystemConfig
from src.data.unsw_nb15 import REQUIRED_COLUMNS

ROOT = Path(__file__).resolve().parents[1]
REAL_RAW = ROOT / "data" / "raw" / "unsw_nb15"


def make_unsw_frame(n_per_class: int = 40, start_id: int = 1, seed: int = 0) -> pd.DataFrame:
    """Small synthetic frame with the official UNSW-NB15 columns (for pipeline tests)."""
    import random
    rng = random.Random(seed)
    classes = ["Normal", "Analysis", "Backdoor", "DoS", "Exploits", "Fuzzers",
               "Generic", "Reconnaissance", "Shellcode", "Worms"]
    rows, next_id = [], start_id
    for ci, cat in enumerate(classes):
        for i in range(n_per_class):
            row = {c: 0 for c in REQUIRED_COLUMNS}
            normal = cat == "Normal"  # one dense (tcp, -) profile so a behavioral baseline exists
            row.update(id=next_id, dur=round(rng.random(), 3), proto="tcp" if normal else ["tcp", "udp"][i % 2],
                       service="-" if normal else ["-", "http", "dns"][i % 3], state=["FIN", "INT", "CON"][ci % 3],
                       spkts=rng.randint(1, 50), dpkts=rng.randint(0, 50), sbytes=rng.randint(40, 5000),
                       dbytes=rng.randint(0, 5000), rate=round(rng.random() * 100, 2), sttl=[31, 62, 254][ci % 3],
                       dttl=[29, 252, 0][ci % 3], sload=round(rng.random() * 1e4, 2), dload=round(rng.random() * 1e4, 2),
                       tcprtt=round(rng.random() / 10, 4), attack_cat=cat, label=0 if cat == "Normal" else 1)
            rows.append(row)
            next_id += 1
    return pd.DataFrame(rows, columns=REQUIRED_COLUMNS)


@pytest.fixture
def data_dir(tmp_path) -> Path:
    """A throwaway data dir with the committed reference data and synthetic raw CSVs."""
    d = tmp_path / "data"
    for sub in ("threat_intel", "baselines", "events"):
        shutil.copytree(ROOT / "data" / sub, d / sub)
    raw = d / "raw" / "unsw_nb15"
    raw.mkdir(parents=True)
    train = make_unsw_frame(40, start_id=1, seed=1)
    test = make_unsw_frame(15, start_id=10_001, seed=2)
    test = pd.concat([test, train.iloc[[0, 50, 90]].assign(id=[20_001, 20_002, 20_003])])  # planted overlap
    train = pd.concat([train, train.iloc[[5, 6]]])  # planted exact duplicates (same id -> dedup)
    train.to_csv(raw / "UNSW_NB15_training-set.csv", index=False)
    test.to_csv(raw / "UNSW_NB15_testing-set.csv", index=False)
    return d


@pytest.fixture
def stub_config(data_dir, tmp_path) -> SystemConfig:
    return SystemConfig(llm_backend="stub", data_dir=data_dir, runs_dir=tmp_path / "runs")


@pytest.fixture
def demo_events() -> list[dict]:
    return json.loads((ROOT / "data" / "events" / "demo_events.json").read_text())
