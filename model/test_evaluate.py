"""Evaluate a frozen selection once. Never changes estimator or threshold."""
import json
import math
from pathlib import Path

import joblib
import numpy as np

from model.evaluation import metrics
from model.train import digest, load_partition


def wilson(success, total):
    if not total:
        return [0., 1.]
    z=1.95996398454
    p=success/total
    denominator=1+z*z/total
    center=(p+z*z/(2*total))/denominator
    half=z*math.sqrt(p*(1-p)/total+z*z/(4*total*total))/denominator
    return [max(0.,center-half),min(1.,center+half)]


def main():
    output=Path('docs/evidence/test-evaluation.json')
    if output.exists():
        raise SystemExit('Test report already exists; no silent repeated selection.')
    selection=Path('docs/evidence/model-selection.json')
    manifest=json.loads(selection.read_text())
    artifact=Path('artifacts/model.joblib')
    if digest(artifact)!=manifest['model_sha256']:
        raise ValueError('Model checksum mismatch')
    if digest('docs/evidence/data-validation.json')!=manifest['data_report_sha256']:
        raise ValueError('Data report changed since selection')
    model=joblib.load(artifact)  # Only the trusted local artifact from this build.
    x,y=load_partition('test')
    scores=model.predict_proba(x)[:,1]
    m=metrics(y,scores,manifest['threshold'])
    bins=[]
    for lo,hi in zip(np.linspace(0,1,11)[:-1],np.linspace(0,1,11)[1:],strict=True):
        keep=(scores>=lo)&((scores<hi) if hi<1 else (scores<=hi))
        bins.append({'lower':float(lo),'upper':float(hi),'count':int(keep.sum()),
                     'mean_score':float(scores[keep].mean()) if keep.any() else None,
                     'observed_fraction':float(y.to_numpy()[keep].mean()) if keep.any() else None})
    result={'selection_sha256':digest(selection),'model_sha256':digest(artifact),
            'model_version':manifest['model_version'],'threshold':manifest['threshold'],
            'test_rows':len(y),'fraud_labels':int(y.sum()),'metrics':m,
            'recall_wilson_95':wilson(m['tp'],m['tp']+m['fn']),
            'precision_wilson_95':wilson(m['tp'],m['tp']+m['fp']),
            'interval_caveat':'Binomial approximation; temporal dependence not modelled.',
            'calibration_bins':bins,'threshold_changed':False}
    output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
