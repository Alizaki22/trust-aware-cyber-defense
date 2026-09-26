# UNSW-NB15 Dataset

## Source

University of New South Wales (UNSW).

Official dataset:
https://research.unsw.edu.au/projects/unsw-nb15-dataset

## Dataset

UNSW-NB15.

## Project Use

Primary dataset for the Detection Agent.

## Files

- UNSW_NB15_training-set.csv
- UNSW_NB15_testing-set.csv

## Preprocessing

1. Load raw CSV files.
2. Clean column names.
3. Remove completely empty records.
4. Replace infinite values.
5. Remove duplicate records.
6. Validate `label`.
7. Validate `attack_cat`.
8. Create training/validation/test datasets.
9. Convert records to Detection Agent instruction format.

## Split

Training: 90% of official training set
Validation: 10% of official training set
Test: official UNSW-NB15 testing set

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

## Citation

Moustafa, N., & Slay, J. (2015).
UNSW-NB15: A comprehensive data set for network intrusion detection systems.
Military Communications and Information Systems Conference (MilCIS).
