# Phase 2 — data acceptance and pipeline

Historical milestone snapshot. Current status: local Compose verification PASSED per user execution report; hosted CI/deployment pending. See [release readiness](release-readiness.md) for superseding gate status.

Objective: replace the provisional dataset assumption with executable, reproducible evidence before model fitting.

## Acceptance criteria and observed outcome
- Publisher and licence identified: PASS, Kaggle ULB version 3; ODbL/DbCL links recorded.
- Actual bytes acquired without fabricated records: PASS, 150,828,752-byte CSV with SHA256 in source manifest.
- Exact schema, numeric/finite inputs and labels checked: PASS.
- Imbalance and duplicate policy measured: PASS, see data card and JSON report.
- Chronological partitions with both classes and disjoint non-time signatures: PASS.
- Full-data repeated run produces identical partition hashes: see data-reproducibility.json.
- Meaningful automated checks: 16 new data checks; 33 total tests including prior API foundation.
- No raw data, secrets or unsupported model results in the repository: data ignored; tracked-file audit performed. No security certification implied.

## Actual decisions
ADR11: accept version 3 using publisher licence metadata and official licence texts; preserve provenance and do not package raw/processed CSVs.
ADR12: remove 1,081 exact duplicates and conservatively exclude 2,281 later-partition repeated non-time vectors. Reason: prevent repeated observations making evaluation easier. Trade-off: this is a curated subset, not directly comparable to results from random splits of the whole benchmark.
ADR13: retain chronological evaluation despite only 57/74 validation/test positives. Reason: preserve future-facing evaluation. Report uncertainty and confusion-matrix counts; do not reshuffle to obtain a better-looking score.
ADR14: lock file SHA256 and exact ordered features. Backend integration must map the provisional v[28] list to V1..V28 explicitly; Class never enters inference.

## Workstream handoff
WS1 now supplies a verified feature list and data report to WS2. WS3 may design the schema around that contract. WS1 still owes a trained artifact, evaluation and threshold. WS2 /predict remains deliberately unavailable. No dashboard milestone is declared complete by this handoff.

## RAID updates
R01 source/use terms: resolved for this local research build; publication of data/model assets still requires licence review.
A01 free acquisition: verified, no paid service or credentials used.
R03 leakage: project duplicate/split controls implemented; upstream PCA and missing cardholder identity remain limitations.
R04 small positive counts: confirmed; numerical uncertainty must accompany future evaluation.
I01 Docker/PostgreSQL runtime limitation: unchanged; no database/container evidence yet.

## Actual issue and recovery
The initial project environment could not install dependencies through the restricted network. Permitted installation succeeded. This is an environment issue, not a simulated production outage. No CI failure or cloud rollback scenario has been claimed.

## Release position
Local data milestone only. No model performance, end-to-end prediction, hosted CI or deployment results exist. Phase 3 will compare a dummy reference, logistic regression and a bounded random forest using training/validation only; phase 4 freezes the threshold before final test evaluation.

## TPM learning
What is a data contract? An explicit list of fields, types and meanings. Here it prevents the API from sending features in an order different from training. A TPM tracks downstream consumers and requires coordinated change.

What is leakage? Information that makes evaluation unrealistically easy. Here chronological separation and duplicate exclusions reduce project-controlled leakage; they cannot establish how the upstream PCA was fitted.

Why a checksum? It identifies the exact file used. A URL can serve changed bytes. Here both download and ingestion reject a mismatch with the accepted dataset.

Credible interview answer: “I used AI assistance to implement a reproducible data-validation milestone. I tracked dataset provenance, documented chronological splits and duplicate exclusions, and kept model performance claims gated until training and evaluation. The small number of positive cases is an explicit limitation.”

## Knowledge check
1. Why is a 99% accuracy result potentially poor on this dataset?
2. Why remove repeated feature vectors from later partitions?
3. What should the pipeline do if the download URL returns different bytes tomorrow?
4. Why must the 57 validation fraud cases influence how confidently we discuss results?
