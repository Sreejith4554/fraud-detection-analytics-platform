"""Binary evaluation and validation-only illustrative cost selection."""
import numpy as np
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def metrics(y, scores, threshold):
    prediction = np.asarray(scores) >= threshold
    tn, fp, fn, tp = confusion_matrix(y, prediction, labels=[0, 1]).ravel()
    return dict(precision=float(precision_score(y, prediction, zero_division=0)),
                recall=float(recall_score(y, prediction, zero_division=0)),
                f1=float(f1_score(y, prediction, zero_division=0)),
                roc_auc=float(roc_auc_score(y, scores)),
                average_precision=float(average_precision_score(y, scores)),
                brier_score=float(brier_score_loss(y, scores)),
                tn=int(tn), fp=int(fp), fn=int(fn), tp=int(tp),
                flagged_per_1000=float(prediction.mean()*1000))


def choose_threshold(y, scores, fn_cost=20):
    y, scores = np.asarray(y), np.asarray(scores)
    if len(y) != len(scores) or not len(y) or set(np.unique(y)) != {0, 1}:
        raise ValueError('Need matching nonempty scores and both binary classes')
    if not np.isfinite(scores).all() or (scores < 0).any() or (scores > 1).any():
        raise ValueError('Scores must be finite probabilities')
    if fn_cost <= 0:
        raise ValueError('Missed-fraud cost must be positive')
    order = np.argsort(-scores, kind='stable')
    s, labels = scores[order], y[order]
    ends = np.r_[np.flatnonzero(s[:-1] != s[1:]), len(s)-1]
    tp = np.cumsum(labels)[ends]
    fp = ends+1-tp
    fn = y.sum()-tp
    candidates = [(float(fn_cost*y.sum()), int(y.sum()), 0, float(np.nextafter(1., 2.)))]
    candidates += [(float(fn_cost*n+p), int(n), int(t+p), float(v))
                   for n,p,t,v in zip(fn,fp,tp,s[ends],strict=True)]
    cost, _, _, threshold = min(candidates)
    return {'threshold': threshold, 'cost': cost, 'fn_cost': fn_cost, 'fp_cost': 1,
            'cost_status': 'SIMULATED', 'metrics': metrics(y, scores, threshold)}
