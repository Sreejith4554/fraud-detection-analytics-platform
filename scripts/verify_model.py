"""Rebuild selected training-only pipeline and compare against frozen artifact."""
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from model.train import digest, load_partition

manifest=json.loads(Path('docs/evidence/model-selection.json').read_text())
assert manifest['selected_model']=='logistic_balanced'
assert digest('artifacts/model.joblib')==manifest['model_sha256']
x,y=load_partition('train')
vx,_=load_partition('validation')
recreated=make_pipeline(StandardScaler(),LogisticRegression(
    max_iter=2000,class_weight='balanced',random_state=42))
recreated.fit(x,y)
restored=joblib.load('artifacts/model.joblib')
delta=float(np.max(np.abs(recreated.predict_proba(vx)[:,1]-restored.predict_proba(vx)[:,1])))
assert delta < 1e-12
# Confirm preprocessing learned training statistics only.
assert np.allclose(restored[0].mean_,x.mean().to_numpy(),rtol=1e-12,atol=1e-12)
report={'retrained_validation_max_probability_difference':delta,
        'scaler_matches_training_only_means':True,
        'validation_rows_compared':len(vx),'artifact_hash_verified':True,
        'test_partition_read':False}
Path('docs/evidence/model-reproducibility.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
