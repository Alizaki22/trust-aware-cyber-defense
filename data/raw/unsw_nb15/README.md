# UNSW-NB15 Dataset

## Source

University of New South Wales (UNSW).

Official dataset:
https://research.unsw.edu.au/projects/unsw-nb15-dataset

## Dataset

UNSW-NB15.

## Project Use

Primary dataset for the Detection Agent (Day 2 dataset preparation).

## Files

- `UNSW_NB15_training-set.csv`
- `UNSW_NB15_testing-set.csv`

These files are not committed to the repository (see `.gitignore`);
download them from the official source above and place them in this
directory before running `scripts/prepare_unsw_nb15.py`.

## Official Train/Test Partition

The official UNSW-NB15 train/test partition is preserved:

- The official **training** file is split 90% train / 10% validation.
- The official **testing** file is used, unmodified, as the test set.
  It is never re-split or replaced with a newly random-split test
  set.

## Preprocessing Performed

Run via `scripts/prepare_unsw_nb15.py` (the single canonical pipeline
for this dataset):

1. Load raw CSV files.
2. Validate schema (all 49 expected UNSW-NB15 columns present).
3. Clean column names.
4. Remove completely empty records.
5. Remove duplicate records.
6. Validate `label` (coerced to numeric, invalid rows dropped,
   confirmed binary 0/1).
7. Validate `attack_cat` distribution.
8. Split into train (90% of official train) / validation (10% of
   official train) / test (official test set, unmodified).
9. **Deduplicate each split independently** on the reduced Detection
   feature set (the 14 `DETECTION_FEATURES` below, plus `attack_cat`
   and `label`). Many raw UNSW-NB15 rows differ only in columns we
   exclude from the model input (`id`, ports, `ct_*` counters,
   etc.), so after feature reduction a large share of rows (commonly
   ~45% in the official train/test files) become exact duplicates of
   the same (input, output) pair. Deduplication removes those before
   saving, so the model isn't trained/evaluated on many copies of
   the same example. This is done per split, never across splits, so
   the official train/validation/test boundary is untouched.
   Feature-combinations that map to more than one `label` are
   reported (not removed) as a data-quality note.
10. Convert each record to the Detection Agent instruction format
    (see below).

Because of step 9, `data/splits/*.csv` and `data/splits/*.jsonl` will
have noticeably fewer rows than the raw official train/test files --
that's expected, not a bug. The exact/pre-dedup counts and the
number removed are printed by the pipeline and can be diffed against
the raw file's row count.

## Preprocessing NOT Performed

- **No StandardScaler / z-score normalization** is applied to the
  Detection Agent's (LLM) text input. Raw feature values (byte
  counts, packet counts, duration, protocol, service, state, etc.)
  are kept as meaningful, human-readable quantities rather than
  scaled numbers. Normalization is appropriate for traditional ML
  models operating on the full numeric feature matrix, but not for
  text fed to an LLM.

## Selected Detection Features

The Detection Agent's model **input** is limited to 14 raw
network-flow features, not all ~49 UNSW-NB15 columns:

| Feature | Why it's included |
|---|---|
| `dur` | Connection duration |
| `proto` | Protocol identity |
| `service` | Service identity |
| `state` | Connection state |
| `spkts` / `dpkts` | Packet-count volume/shape (source/dest) |
| `sbytes` / `dbytes` | Byte-count volume/shape (source/dest) |
| `rate` | Overall traffic rate |
| `sttl` / `dttl` | TTL anomalies are a strong signal for several UNSW-NB15 attack categories |
| `sload` / `dload` | Throughput anomalies (source/dest) |
| `tcprtt` | TCP handshake timing anomalies |

## Excluded Fields

- **`label`** and **`attack_cat`** are the ground-truth target
  fields. They are never included in the Detection Agent's model
  input (see `TARGET_FIELDS` / `create_detection_input()` in
  `scripts/prepare_unsw_nb15.py`); they only appear in the JSONL
  `output` field as the answer.
- `id` is a row identifier, not a network-flow feature, and is
  excluded from the input for the same reason.
- The remaining UNSW-NB15 columns not listed above (e.g. the
  `ct_*` contextual counters, `swin`/`dwin`, `stcpb`/`dtcpb`,
  `sinpkt`/`dinpkt`, `sjit`/`djit`, `smean`/`dmean`, `trans_depth`,
  `response_body_len`, `is_ftp_login`, `ct_ftp_cmd`,
  `ct_flw_http_mthd`, `is_sm_ips_ports`) are kept in the saved CSV
  splits (`data/splits/*.csv`) for auditing / potential non-LLM use,
  but are **not** shown to the Detection Agent.

## Final Output Format

`scripts/prepare_unsw_nb15.py` writes, per split
(`train` / `validation` / `test`), to `data/splits/`:

- `<split>.csv` — full-column cleaned data for that split.
- `<split>.jsonl` — Detection Agent instruction-tuning format:

```json
{
  "instruction": "You are the Detection Agent. Analyze the network security event and determine whether it is normal or malicious. If malicious, identify the attack category.",
  "input": "Analyze this network security event:\ndur=0.121478, proto=tcp, service=-, state=FIN, spkts=6, dpkts=4, sbytes=258, dbytes=172, rate=74.087490, sttl=252, dttl=254, sload=8495.365234, dload=5065.542969, tcprtt=0.000000",
  "output": "{\"classification\": \"Normal\", \"label\": 0}"
}
```

## Labels

`label`:
- 0 = normal
- 1 = attack

`attack_cat`:
- Fuzzers
- Analysis
- Backdoors
- DoS
- Exploits
- Generic
- Reconnaissance
- Shellcode
- Worms

## Validation

`scripts/validate_detection_dataset.py` checks, for each of
`train.jsonl` / `validation.jsonl` / `test.jsonl`:

- required top-level fields present (`instruction`, `input`, `output`)
- `output` parses as JSON with `classification` and `label`
- no label leakage into the model input
- no `attack_cat` leakage into the model input
- input feature count matches the canonical 14-feature list
- `label` is binary (0/1)
- no malformed / unparsable JSONL lines
- no exact-duplicate records within a split (the generator now
  removes these at preparation time -- see "Deduplication" above --
  so this should always report 0 on output from
  `prepare_unsw_nb15.py`)
- class/label distributions (reported, not enforced)

## Citation

Moustafa, N., & Slay, J. (2015).
UNSW-NB15: A comprehensive data set for network intrusion detection systems.
Military Communications and Information Systems Conference (MilCIS).
