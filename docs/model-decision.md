# Frozen model decision — before test evaluation
Model: class-weighted logistic regression, preceded by a StandardScaler fitted on training only. Seed 42, max_iter 2000. Compare with dummy prior, unweighted logistic regression and a 100-tree, depth-12 random forest with min leaf size 2 and balanced-subsample weighting. No resampling, no tuning sweep or GPU.

Selection rule implemented before fitting: highest validation average precision; tie-break simulated cost at FN:FP=20:1, then model name. Weighted logistic AP 0.77269 versus random forest 0.76615, unweighted logistic 0.64244 and dummy 0.001015. This small lead on only 57 fraud labels is not evidence of statistically superior generalisation.

Chosen threshold: 0.9996296180470535, selected on validation by minimizing 20*FN + FP. Costs are SIMULATED review trade-offs, not money or banking estimates. Ties prefer fewer false negatives, then fewer flags. Threshold equality triggers review. A threshold above 1 is permitted only as the no-review candidate during optimization; it was not selected for the chosen model.

Validation operating point: TP 44, FN 13, FP 25, TN 56102. Default 0.5: TP 51, FN 6, FP 1923. Reducing false reviews trades away detection of seven fraud-labelled validation cases. Weighted probabilities are poorly calibrated: validation Brier score 0.02980 (worse than dummy 0.001014). The unusually high selected threshold reflects this score distribution. Outputs must be described as model estimates/scores, not real-world probabilities.

Counter-evidence retained: random forest at its threshold achieves TP 43, FN 14, FP 2 and simulated cost 282, versus 285 for the selected model. It has better precision and Brier score. AP-first was the planned ranking objective, so the selected model is not called the best operational or best-calibrated system. A future change to a cost-first objective requires an explicit new experiment and fresh evaluation strategy, not choosing after viewing test performance.

The selected model is saved as artifacts/model.joblib. Reloaded validation probabilities match exactly (maximum absolute difference zero). Manifest includes model and input-data report checksums, ordered features, dependency version, threshold and all candidate metrics. No training on validation after threshold selection. Only local trusted joblib files may be loaded.

The test-evaluation step will read this frozen selection and refuse to overwrite its report. It will not change the estimator or threshold. This file and selection manifest are committed before that step. Test integrity counts were checked in phase 2; test performance has not been consulted at this decision point.
