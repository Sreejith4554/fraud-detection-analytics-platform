import json
from pathlib import Path

import pandas as pd

from model.ingest import SIGNATURE, ingest

baseline=json.loads(Path('docs/evidence/data-validation.json').read_text())
repeated=ingest(Path('data/raw/creditcard.csv'),Path('data/processed'),Path('docs/evidence/data-validation.json'),baseline['source_sha256'])
assert baseline==repeated
parts={name:pd.read_csv(f'data/processed/{name}.csv',float_precision='round_trip') for name in ['train','validation','test']}
signatures={name:set(pd.util.hash_pandas_object(df[SIGNATURE],index=False)) for name,df in parts.items()}
assert not(signatures['train']&signatures['validation'] or signatures['train']&signatures['test'] or signatures['validation']&signatures['test'])
assert parts['train'].Time.max()<parts['validation'].Time.min()<parts['test'].Time.min()
eda=parts['train'].describe(percentiles=[.01,.5,.99]).to_dict()
Path('docs/evidence/training-eda.json').write_text(json.dumps(eda,indent=2)+'\n')
result={'full_dataset_second_run_identical':True,'cross_partition_non_time_signature_overlap':0,'chronology_verified':True,'training_eda_only':True,'total_retained_rows':sum(len(p) for p in parts.values())}
Path('docs/evidence/data-reproducibility.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
