# Dataset

This document describes the datasets considered, selected, and used in this project. No dataset has been finalized — this document tracks candidates, requirements, and decisions as they evolve.

## Dataset Requirements

### General Requirements

All datasets used in this project must:

1. **Be appropriately licensed for academic use.** No proprietary, restricted, or unauthorized data.
2. **Be clearly labeled.** Real data must be labeled as real; synthetic data must be labeled as synthetic.
3. **Be documented.** Source, version, license, and any preprocessing steps must be recorded.
4. **Be relevant.** Data must support the specific agent or evaluation task it is used for.
5. **Contain no real personally identifiable information (PII)** that could identify individuals, or must be properly anonymized.

### Per-Agent Data Needs

| Agent | Data Needed | Purpose |
|---|---|---|
| Detection Agent | Labeled security events with classification labels | Training (Phase 2), evaluation |
| Intelligence Agent | Indicator of compromise (IOC) lookup data | Runtime reference data |
| Behavioral Analysis Agent | Historical behavioral baselines per entity | Runtime reference data |
| Verification Agent | Agent findings paired with original events | Verification logic testing |
| Fine-tuning (Phase 2) | Instruction-formatted cybersecurity examples | LoRA/QLoRA training |
| Evaluation | Labeled test scenarios with expected outcomes | Phase 1 vs. Phase 2 comparison |

## Candidate Datasets

### Network Intrusion Detection

#### CIC-IDS2017

- **Source:** Canadian Institute for Cybersecurity, University of New Brunswick
- **URL:** https://www.unb.ca/cic/datasets/ids-2017.html
- **License:** Available for research purposes
- **Description:** Network traffic flows labeled with attack types including DDoS, Brute Force, Botnets, Port Scan, Web Attacks, and Infiltration. Contains approximately 2.8 million flow records.
- **Format:** CSV files with 80+ network flow features plus labels
- **Attack types:** Benign, FTP-Patator, SSH-Patator, DoS (Slowloris, Slowhttptest, Hulk, GoldenEye), Heartbleed, Web Attack (Brute Force, XSS, SQL Injection), Infiltration, Botnet, Port Scan, DDoS
- **Relevance:** Primary candidate for Detection Agent training and evaluation
- **Considerations:** Class imbalance (benign traffic heavily dominates); may need sampling or balancing

#### UNSW-NB15

- **Source:** University of New South Wales, Canberra
- **URL:** https://research.unsw.edu.au/projects/unsw-nb15-dataset
- **License:** Available for research purposes
- **Description:** Network intrusion dataset with nine modern attack categories, considered more complex and representative than older benchmarks like KDD Cup 99.
- **Format:** CSV files with 49 features plus labels
- **Attack types:** Fuzzers, Analysis, Backdoors, DoS, Exploits, Generic, Reconnaissance, Shellcode, Worms
- **Relevance:** Alternative/complementary dataset for Detection Agent
- **Considerations:** Smaller than CIC-IDS2017; different feature set; useful for cross-dataset validation

### Phishing / Email

Candidates to investigate (not yet evaluated in detail):

- **Nazario phishing corpus** — publicly available phishing email collection.
- **APWG (Anti-Phishing Working Group) datasets** — may require application/membership.
- **SpamAssassin public corpus** — labeled spam/ham email dataset.

### Threat Intelligence

For the Intelligence Agent's IOC lookup functionality:

- **Synthetic IOC dataset** — to be constructed by the team, containing:
  - Known-malicious IP addresses (simulated)
  - Known-malicious domain names (simulated)
  - Known-malicious file hashes (simulated)
  - Labeled as synthetic; not drawn from real threat feeds

- **Public threat intelligence feeds** (for reference, not direct consumption):
  - AlienVault OTX — open threat exchange data
  - Abuse.ch — malware and botnet tracking data

### Behavioral Baselines

For the Behavioral Analysis Agent:

- **Synthetic baselines** — to be constructed by the team, containing:
  - Normal activity profiles per simulated user/host
  - Typical login times, source IPs, accessed resources
  - Labeled as synthetic

The team constructs these to ensure the Behavioral Analysis Agent has something to compare against, since real user behavior data raises privacy concerns.

## Data Format Specifications

### Security Event Input Format

Events entering the system are normalized to a common format (illustrative, not final):

```json
{
  "event_id": "evt-001",
  "timestamp": "2024-03-15T14:32:00Z",
  "event_type": "network_flow",
  "source_ip": "192.168.1.105",
  "destination_ip": "10.0.0.50",
  "destination_port": 443,
  "protocol": "TCP",
  "raw_content": "...",
  "entity": "user-jdoe",
  "metadata": {}
}
```

### Fine-Tuning Data Format

For Phase 2 fine-tuning, data follows an instruction-tuning structure:

```json
{
  "instruction": "You are a Detection Agent. Classify the following security event.",
  "input": "<normalized security event JSON>",
  "output": "{\"classification\": \"ddos_attack\", \"evidence\": \"high volume TCP SYN packets to port 80\", \"confidence\": \"high\", \"reasoning\": \"Traffic pattern matches SYN flood characteristics\"}"
}
```

See `docs/LLM_FINE_TUNING.md` for training data volume and quality requirements.

## Data Preprocessing Pipeline

### Network Flow Data (CIC-IDS2017 / UNSW-NB15)

1. **Load** raw CSV files.
2. **Clean** — handle missing values, infinity values, and malformed records.
3. **Normalize** — scale numerical features to consistent ranges.
4. **Balance** — address class imbalance through sampling (e.g., undersampling majority class, or oversampling minority classes).
5. **Convert** — transform tabular data into text descriptions suitable for LLM input.
6. **Split** — divide into training (80%), validation (10%), test (10%) sets.
7. **Format** — structure into the instruction-tuning format above.

### Synthetic Data

1. **Design** scenarios covering a range of attack types and normal behavior.
2. **Generate** events following the defined input format.
3. **Label** with expected classifications and agent outputs.
4. **Review** manually for quality and consistency.
5. **Document** clearly as synthetic.

## Licensing and Ethical Considerations

- All datasets must be used in accordance with their published license terms.
- No unauthorized data collection or scraping.
- Synthetic data is preferred where possible to avoid privacy concerns.
- Real datasets must not contain unmasked PII.
- All data used in the final report must have its source and license documented.
- The team must not use datasets for purposes beyond their stated license scope.

## Dataset Decisions

| Decision | Status |
|---|---|
| Primary Detection Agent dataset | TO BE DECIDED — CIC-IDS2017 and UNSW-NB15 are candidates |
| Threat intelligence data source | TO BE DECIDED — likely synthetic |
| Behavioral baseline data source | TO BE DECIDED — likely synthetic |
| Phase 2 fine-tuning dataset | TO BE DECIDED — depends on which agent is fine-tuned (D-010) |
| Data preprocessing approach | TO BE DECIDED — depends on selected dataset |

## Related Documentation

- `docs/RESEARCH.md` — Dataset considerations and research background
- `docs/LLM_FINE_TUNING.md` — Training data requirements and format
- `docs/EXPERIMENTS.md` — How datasets are used in experiments
- `docs/DECISIONS.md` (D-010) — Which agent(s) use the fine-tuned model
