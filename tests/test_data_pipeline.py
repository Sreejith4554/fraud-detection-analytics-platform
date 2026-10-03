"""SYNTHETIC fixtures test mechanics only; not ML training/evaluation evidence."""
import json

import numpy as np
import pandas as pd
import pytest

from model.ingest import COLUMNS, FEATURES, SIGNATURE, ingest, partition, validate


def fixture():
    rows = []
    for i in range(100):
        rows.append([float(i), *[float(i + j / 100) for j in range(28)], 10., i % 2])
    return pd.DataFrame(rows, columns=COLUMNS)


@pytest.mark.parametrize('problem', ['missing', 'extra', 'order', 'nan', 'inf',
                                     'negative_amount', 'negative_time', 'label',
                                     'one_class', 'string', 'empty'])
def test_invalid_data_stops_pipeline(problem):
    df = fixture()
    if problem == 'missing':
        df = df.drop(columns='V1')
    elif problem == 'extra':
        df['device'] = 1
    elif problem == 'order':
        df = df[list(reversed(COLUMNS))]
    elif problem == 'nan':
        df.loc[0, 'V1'] = np.nan
    elif problem == 'inf':
        df.loc[0, 'V1'] = np.inf
    elif problem == 'negative_amount':
        df.loc[0, 'Amount'] = -1
    elif problem == 'negative_time':
        df.loc[0, 'Time'] = -1
    elif problem == 'label':
        df.loc[0, 'Class'] = 2
    elif problem == 'one_class':
        df.Class = 0
    elif problem == 'string':
        df.V1 = df.V1.astype(str)
    elif problem == 'empty':
        df = df.iloc[:0]
    with pytest.raises(ValueError):
        validate(df)


def test_conflicting_duplicate_stops_pipeline():
    df = fixture()
    copy = df.iloc[[0]].copy()
    copy.Class = 1
    with pytest.raises(ValueError, match='conflicting'):
        validate(pd.concat([df, copy], ignore_index=True))


def test_chronology_ties_and_disjoint_signatures():
    df = fixture()
    df.loc[59:61, 'Time'] = 60.
    parts, _ = partition(df.sample(frac=1, random_state=42))
    assert parts['train'].Time.max() < parts['validation'].Time.min()
    assert parts['validation'].Time.max() < parts['test'].Time.min()
    sets = [set(pd.util.hash_pandas_object(p[SIGNATURE], index=False)) for p in parts.values()]
    assert not (sets[0] & sets[1] or sets[0] & sets[2] or sets[1] & sets[2])
    assert sum((p.Time == 60).any() for p in parts.values()) == 1


def test_duplicates_and_later_repeats_excluded():
    df = fixture()
    df.loc[85, SIGNATURE] = df.loc[5, SIGNATURE].to_numpy()
    df = pd.concat([df, df.iloc[[0]]], ignore_index=True)
    parts, report = partition(df)
    assert report['exact_duplicate_rows_removed'] == 1
    assert report['non_time_repeat_rows_excluded']['test'] == 1
    assert len(parts['test']) == 19


def test_insufficient_partition_classes_stops():
    df = fixture()
    df.loc[80:, 'Class'] = 0
    with pytest.raises(ValueError, match='test partition'):
        partition(df)


def test_round_trip_determinism_and_checksum_guard(tmp_path):
    source = tmp_path / 'source.csv'
    fixture().to_csv(source, index=False)
    output, report = tmp_path / 'parts', tmp_path / 'report.json'
    first = ingest(source, output, report)
    second = ingest(source, output, report, first['source_sha256'])
    assert first == second == json.loads(report.read_text())
    assert len(pd.read_csv(output / 'train.csv')) == 60
    assert 'Class' not in FEATURES
    with pytest.raises(ValueError, match='checksum'):
        ingest(source, output, report, 'incorrect')
