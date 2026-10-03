# Accepted dataset: ULB / Worldline Credit Card Fraud Detection
**PORTFOLIO PROOF-OF-CONCEPT. Historical research dataset, not live bank traffic.**

Source: https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud
Owner: Machine Learning Group – ULB. Research collaboration: ULB and Worldline.
Acquired version 3 from the publisher's public endpoint on 2 October 2026.
Exact endpoint, byte size and SHA256: [source manifest](provenance/source.json).

## Rights and attribution
The publisher metadata lists “Database: Open Database, Contents: Database Contents”. Applicable published texts:
- https://opendatacommons.org/licenses/odbl/1-0/
- https://opendatacommons.org/licenses/dbcl/1-0/

These are separate from the repository's MIT code licence. Preserve source attribution and licence references. Public redistribution of an adapted database carries ODbL obligations; no original or transformed transaction rows are distributed in this code checkpoint. Recheck obligations before publishing data, model artifacts or sample records. The licence is not a claim of privacy compliance or suitability for financial decisions.

Dataset citation: Andrea Dal Pozzolo, Olivier Caelen, Reid A. Johnson and Gianluca Bontempi, “Calibrating Probability with Undersampling for Unbalanced Classification”, IEEE CIDM, 2015 (citation supplied by the dataset metadata).

## Observed contents
Local validation: 284,807 rows; 492 fraud labels (0.17275%); no missing/nonfinite values; exact expected columns. Inputs: Time, V1–V28, Amount. Target: Class (0/1). Time is elapsed seconds, not a real transaction timestamp. V1–V28 are anonymised PCA components. Original device, location and merchant variables are unavailable. Publisher describes a short historical European cardholder sample; do not generalise to current banking traffic.

## Reproduce
From repository root after installing requirements:
```bash
python -m model.download
python -m model.ingest
PYTHONPATH=. python scripts/verify_data.py
```
Download requires internet access but used no account credentials here. It refuses to overwrite an existing CSV, checks the publisher licence label and verifies the accepted SHA256. If `data/raw/creditcard.csv` already exists, skip download and run ingestion. A changed hash or licence stops the pipeline for review.

Ingestion writes ignored `data/processed/{train,validation,test}.csv` and a tracked aggregate report. The verifier repeats ingestion and compares all report hashes, checks partition overlap, then creates training-only descriptive statistics. No model has been fitted or evaluated yet.

## Partition decision
Stable chronological order, approximate 60/20/20 split, equal-time groups kept together. Remove exact full-input duplicate rows, keeping the earliest source occurrence. Conflicting labels for identical full inputs stop processing. Conservative extra guard: remove later-partition rows whose V1–V28/Amount signature occurred earlier, without consulting their labels. The signature uses pandas' 64-bit hashing; a theoretical collision could conservatively exclude an unrelated row. This guard is not proof of cardholder independence: identifiers are unavailable. Repeated signatures within one partition remain unless full inputs are identical.

| Partition | Rows | Fraud | Non-fraud |
|---|---:|---:|---:|
| Train | 170,235 | 342 | 169,893 |
| Validation | 56,184 | 57 | 56,127 |
| Test | 55,026 | 74 | 54,952 |

1,081 exact duplicate rows removed; an additional 561 validation and 1,720 test rows excluded by the non-time signature guard. Retained total: 281,445 rows and 473 fraud labels. This curated evaluation distribution differs from the source: report both rather than claim untouched benchmark comparability.

Only validation will select model/threshold. The final test set is reserved for evaluation after selection. This milestone inspects test schema/counts/ranges for integrity; it does not examine model performance. Counts of 57 and 74 fraud cases make precision/recall estimates sensitive to individual errors. Upstream PCA fitting provenance is unknown, so only project-controlled leakage is addressed.

## Demo separation
No demo samples created yet. Future hand-authored inputs must be labelled SYNTHETIC and cannot be used as real-data model evidence. Permitted source replays must be labelled DATASET_REPLAY and excluded from training/evaluation claims. Raw and processed CSVs are ignored by Git and excluded from release archives.
