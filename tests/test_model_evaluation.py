import numpy as np
import pytest

from model.evaluation import choose_threshold, metrics


def test_threshold_matches_exhaustive_cost_and_tie_break():
    y = np.array([0, 1, 0, 1, 0, 1])
    scores = np.array([.1, .1, .3, .8, .8, .9])
    for ratio in [5, 20, 100]:
        options = []
        for t in [*np.unique(scores), np.nextafter(1.,2.)]:
            m = metrics(y, scores, t)
            options.append((ratio*m['fn']+m['fp'], m['fn'], m['tp']+m['fp'], t))
        result = choose_threshold(y, scores, ratio)
        assert result['threshold'] == min(options)[3]
        assert result['cost'] == min(options)[0]


def test_threshold_boundary_and_confusion_matrix():
    result = metrics([0, 1, 1, 0], [.1, .5, .4, .9], .5)
    assert [result[k] for k in ['tn','fp','fn','tp']] == [1,1,1,1]
    assert result['precision'] == result['recall'] == .5


@pytest.mark.parametrize('scores', [[np.nan,.5], [-.1,.5], [.1,1.1]])
def test_invalid_probabilities_rejected(scores):
    with pytest.raises(ValueError):
        choose_threshold([0,1], scores)


def test_all_ties_are_processed_together():
    result = choose_threshold([0,0,0,1], [.2]*4, fn_cost=20)
    assert result['threshold'] == .2
    assert result['metrics']['tp'] == 1
    assert result['metrics']['fp'] == 3

