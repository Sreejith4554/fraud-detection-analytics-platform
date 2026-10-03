"""Recreate the selected artifact from pinned training data, without opening test."""
import json
from pathlib import Path

import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from model.train import digest, load_partition


def main():
    manifest=json.loads(Path('docs/evidence/model-selection.json').read_text())
    destination=Path('artifacts/model.joblib')
    if destination.exists():
        if digest(destination)!=manifest['model_sha256']:
            raise ValueError('Existing model hash mismatch; investigate before replacing')
        print('Verified existing artifact')
        return
    if manifest['selected_model']!='logistic_balanced':
        raise ValueError('This restoration script supports only the frozen v1 model')
    x,y=load_partition('train')
    model=make_pipeline(StandardScaler(),LogisticRegression(
        max_iter=2000,class_weight='balanced',random_state=42))
    model.fit(x,y)
    destination.parent.mkdir(exist_ok=True)
    temporary=destination.with_suffix('.part')
    try:
        joblib.dump(model,temporary)
        if digest(temporary)!=manifest['model_sha256']:
            raise ValueError('Rebuilt bytes differ: check pinned dependencies and runtime; do not silently accept')
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    print('Restored artifact; exact frozen SHA256 matched; test set not read')


if __name__=='__main__':
    main()
