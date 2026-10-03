"""Validate the source and create deterministic chronological partitions."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from pandas.api.types import is_bool_dtype, is_numeric_dtype

FEATURES = ['Time', *[f'V{i}' for i in range(1, 29)], 'Amount']
COLUMNS = [*FEATURES, 'Class']
SIGNATURE = FEATURES[1:]  # Detect repeat vectors even when elapsed time differs.


def validate(frame):
    if list(frame.columns) != COLUMNS:
        raise ValueError('Expected exact ordered columns: Time,V1..V28,Amount,Class')
    if frame.empty:
        raise ValueError('Dataset is empty')
    if any(not is_numeric_dtype(t) or is_bool_dtype(t) for t in frame.dtypes):
        raise ValueError('All fields must be numeric, not boolean')
    if not np.isfinite(frame.to_numpy(dtype=float)).all():
        raise ValueError('Missing or nonfinite values')
    if (frame[['Time', 'Amount']] < 0).any().any():
        raise ValueError('Time and Amount must be nonnegative')
    if not frame.Class.isin([0, 1]).all() or frame.Class.nunique() != 2:
        raise ValueError('Class must contain both binary labels 0 and 1')
    # Ambiguous identical full inputs cannot be silently resolved.
    repeated = frame[frame.duplicated(FEATURES, keep=False)]
    if not repeated.empty and repeated.groupby(FEATURES, dropna=False).Class.nunique().gt(1).any():
        raise ValueError('Identical inputs have conflicting labels')


def partition(frame):
    validate(frame)
    ordered = frame.sort_values('Time', kind='stable')
    # Keep earliest occurrence; this decision is label-independent.
    clean = ordered.drop_duplicates(FEATURES, keep='first')
    n = len(clean)
    boundary1 = float(clean.iloc[int(n * .6)].Time)
    boundary2 = float(clean.iloc[int(n * .8)].Time)
    raw_parts = [clean[clean.Time < boundary1],
                 clean[(clean.Time >= boundary1) & (clean.Time < boundary2)],
                 clean[clean.Time >= boundary2]]
    parts, excluded = {}, {}
    seen = set()
    for name, part in zip(['train', 'validation', 'test'], raw_parts, strict=True):
        signatures = pd.util.hash_pandas_object(part[SIGNATURE], index=False)
        # Conservatively discard later-partition repeats; keep within-partition records.
        keep = ~signatures.isin(seen)
        retained = part.loc[keep]
        excluded[name] = int((~keep).sum())
        if retained.empty or retained.Class.nunique() != 2:
            raise ValueError(f'{name} partition must contain both labels')
        parts[name] = retained
        seen.update(signatures.tolist())
    return parts, {
        'exact_duplicate_rows_removed': len(frame) - len(clean),
        'non_time_repeat_rows_excluded': excluded,
        'time_boundaries': [boundary1, boundary2],
    }


def describe(frame):
    return {
        'rows': len(frame), 'fraud': int(frame.Class.sum()),
        'nonfraud': int((frame.Class == 0).sum()),
        'fraud_fraction': float(frame.Class.mean()),
        'time_min': float(frame.Time.min()), 'time_max': float(frame.Time.max()),
        'amount_min': float(frame.Amount.min()), 'amount_max': float(frame.Amount.max()),
    }


def ingest(source, output, report_path, expected_sha=None):
    with source.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if expected_sha is not None and digest != expected_sha:
        raise ValueError('Source checksum does not match accepted provenance')
    frame = pd.read_csv(source, float_precision='round_trip')
    parts, decisions = partition(frame)
    report = {'source_sha256': digest, 'features': FEATURES,
              'source': describe(frame), 'missing_cells': int(frame.isna().sum().sum()),
              'partition_method': 'chronological 60/20/20; equal timestamps unsplit',
              **decisions, 'partitions': {}}
    output.mkdir(parents=True, exist_ok=True)
    for name, part in parts.items():
        path = output / f'{name}.csv'
        part.to_csv(path, index=False)
        with path.open('rb') as stream:
            part_digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        report['partitions'][name] = {
            **describe(part), 'sha256': part_digest,
            'source_row_ids_sha256': hashlib.sha256(
                np.asarray(part.index, dtype='<i8').tobytes()).hexdigest(),
        }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=Path('data/raw/creditcard.csv'))
    parser.add_argument('--output', type=Path, default=Path('data/processed'))
    parser.add_argument('--report', type=Path, default=Path('docs/evidence/data-validation.json'))
    args = parser.parse_args()
    provenance = json.loads(Path('data/provenance/source.json').read_text())
    print(json.dumps(ingest(args.source, args.output, args.report, provenance['sha256']), indent=2))


if __name__ == '__main__':
    main()
