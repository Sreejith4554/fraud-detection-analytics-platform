# Phases 3–4: baseline model and threshold evaluation

Historical milestone snapshot. The statements below preserve the project state at this phase and are not the current release status. The completed proof-of-concept now has verified local Docker Compose execution, passing hosted GitHub integration and container gates, CodeQL analysis, and browser demonstration evidence. See [release readiness](release-readiness.md) for the authoritative current status.

**TESTED offline model milestone; PORTFOLIO PROOF-OF-CONCEPT.**

## Objective and acceptance
Train interpretable baselines, select using validation only, freeze the choice, evaluate once on the held-out test partition and preserve the real artifact. Achieved: four candidates fitted, preprocessing fitted only on training, all required metrics recorded, selected artifact serialized/reloaded, threshold decision committed before test execution. Model probabilities are genuine predict_proba outputs, not invented values.

## Validation comparison
| Model | Average precision | ROC-AUC | Selected FP | Selected FN | Simulated cost (20 FN + FP) |
|---|---:|---:|---:|---:|---:|
| Dummy prior | 0.001015 | 0.5000 | 0 | 57 | 1140 |
| Logistic regression | 0.64244 | 0.96792 | 63 | 11 | 283 |
| Weighted logistic regression | 0.77269 | 0.97078 | 25 | 13 | 285 |
| Random forest | 0.76615 | 0.94762 | 2 | 14 | 282 |

Operating counts use each candidate's own validation-selected cost20 threshold. Weighted logistic wins the predeclared AP-first rule, not every business metric. Its narrow AP lead does not demonstrate statistical superiority. Random forest has stronger precision and lower Brier score; preserve this counter-evidence.

## Frozen choice and test result
Model version ulb-v1: StandardScaler + class-weighted logistic regression. Threshold 0.9996296180470535. Freeze commit: 72f8398. Model-selection manifest represents the decision before test was opened; its NOT_OPENED marker is historical. The separate test-evaluation report records the later evaluation without rewriting the decision.

55,026 test records; 74 fraud labels. TP 55, FN 19, FP 21, TN 54,931.

| Metric | Held-out result |
|---|---:|
| Precision | 0.723684 |
| Recall | 0.743243 |
| F1 | 0.733333 |
| ROC-AUC | 0.981522 |
| Average precision | 0.747563 |
| Brier score | 0.023960 |
| Flags per 1,000 records | 1.381165 |

Average precision summarizes the precision-recall curve; it is not silently equated with trapezoidal PR-AUC. The complete validation PR curve is recorded. No accuracy headline is used.

Approximate 95% Wilson intervals: precision 61.4–81.2%; recall 63.3–82.9%. These assume binomial observations; temporal dependence and dataset bias are not represented. No confidence interval for model superiority is claimed.

## False-positive decision: observed results, simulated costs
This is an actual offline evaluation finding, not a simulated incident. At threshold 0.5, weighted logistic produced 1,923 false positives and missed 6 validation fraud cases. The selected threshold reduces false positives to 25 but misses 13 cases. Cost ratios 5,20,100 are SIMULATED assumptions, not financial values or institution-specific estimates. They are available in the selection JSON for sensitivity review.

Product impact: “review triggered” is appropriate; “payment declined” is not. A high ranking score is not established calibrated risk. Test calibration bins show substantial overconfidence; for example the broad 0.9–1.0 bin has mean score around 0.966 but observed fraud fraction around 0.240. This broad bin is not the selected-threshold precision estimate. Brier score and bins are reported rather than hidden.

Calibration is a documented technical debt item. Any future calibrator needs a separate training/validation design; do not fit it on this already-opened test set. API field `fraud_probability`, if retained for contract continuity, must include an explicit uncalibrated-model-score explanation. Prefer `model_score` in the displayed UI. This decision blocks any claim of reliable financial probability.

## Reproduction and trusted artifact
Pinned environment and data from Phase 2 are required. To restore the exact selected artifact from a clone:
```bash
python -m model.download  # skip if accepted raw CSV already exists
python -m model.ingest
PYTHONPATH=. OPENBLAS_NUM_THREADS=2 python scripts/restore_model.py
PYTHONPATH=. OPENBLAS_NUM_THREADS=2 python scripts/verify_model.py
python -m pytest -q
```
The restore command trains only on train.csv and requires an exact frozen model SHA256 match. Platform or dependency differences may change serialized bytes; a mismatch stops restoration and requires an explicit new version, not bypassing the check.

`python -m model.train` and `python -m model.test_evaluate` are the original experiment entry points. They deliberately refuse to overwrite an existing model/test report. Do not delete the test report merely to retry selection. New experiments require a versioned workspace and evaluation plan. No full training process occurs inside the API.

The selected joblib artifact is supplied in the private milestone package for continuation, excluded from Git. Never load untrusted pickle/joblib files. MIT applies to code, not dataset rights. Source and ODbL/DbCL references remain in the data card; external publication of model/data assets remains a release review item. Raw/processed transactions are not packaged.

## Verification and handoff
39 automated tests pass, including six new threshold/metric tests. Tests validate equality at threshold, tied scores, cost selection against brute-force alternatives, nonfinite/out-of-range rejection and confusion-matrix orientation. Real-data verification separately reloads and retrains the selected pipeline: validation probabilities match with maximum difference zero across 56,184 rows; scaler means match training-only statistics. This is stronger evidence than counting test files.

WS1 hands WS2 the model artifact, ordered feature list, schema version, threshold, hash and limitations. WS2 still owes real API inference and safe loading; WS3 still owes PostgreSQL persistence. Current HTTP prediction endpoint remains 503. No Docker, cloud or production system claim follows from offline training.

## TPM knowledge check — Phase 3
1. What is the difference between training a model and using it for inference?
2. Why must the scaler be fitted on training data only?
3. Why compare against a dummy model?

## TPM knowledge check — Phase 4
1. Why did raising the threshold reduce false positives but increase missed fraud?
2. Why is 0.99963 not evidence of 99.963% real-world fraud certainty?
3. Why can we not switch to a different model merely because we dislike this test result?

Credible interview answer: “In an AI-assisted portfolio build, I followed a documented model-selection and release process, preserved contrary evidence and tracked the dependency between the artifact and API. I can explain how threshold choice changes review workload and missed cases. The model is an offline baseline with calibration limitations, not a banking-grade system.”
