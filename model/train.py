"""Train on train.csv; select on validation.csv. Never opens test.csv."""
import hashlib
import json
import platform
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_recall_curve
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from model.evaluation import choose_threshold, metrics
from model.ingest import FEATURES


def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def load_partition(name):
    manifest = json.loads(Path('docs/evidence/data-validation.json').read_text())
    path = Path(f'data/processed/{name}.csv')
    if digest(path) != manifest['partitions'][name]['sha256']:
        raise ValueError('Partition checksum mismatch')
    df = pd.read_csv(path, float_precision='round_trip')
    return df[FEATURES], df.Class.astype(int)


def main():
    artifact = Path('artifacts/model.joblib')
    if artifact.exists() or Path('docs/evidence/test-evaluation.json').exists():
        raise SystemExit('Existing experiment: refusing overwrite. Version a new experiment explicitly.')
    x, y = load_partition('train')
    vx, vy = load_partition('validation')
    candidates = {
        'dummy': DummyClassifier(strategy='prior'),
        'logistic': make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, random_state=42)),
        'logistic_balanced': make_pipeline(StandardScaler(), LogisticRegression(
            max_iter=2000, class_weight='balanced', random_state=42)),
        'random_forest': RandomForestClassifier(n_estimators=100, max_depth=12,
            min_samples_leaf=2, class_weight='balanced_subsample', n_jobs=2, random_state=42),
    }
    reports, models, predictions = {}, {}, {}
    for name, estimator in candidates.items():
        start = time.perf_counter()
        estimator.fit(x, y)
        scores = estimator.predict_proba(vx)[:, 1]
        reports[name] = {'fit_and_validation_seconds': time.perf_counter()-start,
                         'at_0_5': metrics(vy, scores, .5),
                         'cost_sensitivity': {str(c): choose_threshold(vy, scores, c) for c in [5,20,100]}}
        models[name], predictions[name] = estimator, scores
        print(name, json.dumps(reports[name]), flush=True)
    # Predeclared: maximum validation AP; then simulated operating cost; then name.
    eligible = [n for n in models if n != 'dummy']
    chosen = min(eligible, key=lambda n: (-reports[n]['at_0_5']['average_precision'],
                                        reports[n]['cost_sensitivity']['20']['cost'], n))
    selected = reports[chosen]['cost_sensitivity']['20']
    artifact.parent.mkdir(exist_ok=True)
    joblib.dump(models[chosen], artifact)
    restored = joblib.load(artifact)
    delta = float(np.max(np.abs(restored.predict_proba(vx)[:,1]-predictions[chosen])))
    assert delta == 0
    precision, recall, thresholds = precision_recall_curve(vy, predictions[chosen])
    # Full validation PR curve, aggregate operating points only, no source rows.
    Path('docs/evidence/validation-pr-curve.json').write_text(json.dumps({
        'precision': precision.tolist(), 'recall': recall.tolist(), 'thresholds': thresholds.tolist()}))
    manifest = {'model_version': 'ulb-v1', 'selected_model': chosen,
                'selection_rule': 'validation AP descending; cost20 ascending; name ascending',
                'schema_version': '1', 'features': FEATURES, 'threshold': selected['threshold'],
                'threshold_cost_status': 'SIMULATED FN=20 FP=1',
                'model_sha256': digest(artifact), 'seed': 42,
                'python': platform.python_version(), 'sklearn': sklearn.__version__,
                'data_report_sha256': digest('docs/evidence/data-validation.json'),
                'reload_max_probability_difference': delta,
                'test_evaluation_status': 'NOT_OPENED', 'validation_results': reports}
    Path('docs/evidence/model-selection.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print('SELECTED', chosen, 'THRESHOLD', selected['threshold'], flush=True)


if __name__ == '__main__':
    main()
