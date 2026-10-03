"""Acquire the pinned public Kaggle dataset; never redistribute raw data here."""
import hashlib
import json
import shutil
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

URL = 'https://www.kaggle.com/api/v1/datasets/download/mlg-ulb/creditcardfraud?datasetVersionNumber=3'
EXPECTED_SHA256 = '76274b691b16a6c49d3f159c883398e03ccd6d1ee12d9d8ee38f4b4b98551a89'
METADATA = 'https://www.kaggle.com/api/v1/datasets/list?search=creditcardfraud'


def main():
    raw = Path('data/raw')
    raw.mkdir(parents=True, exist_ok=True)
    target = raw / 'creditcard.csv'
    if target.exists():
        raise SystemExit('Raw file already exists; refusing to overwrite. Validate it instead.')
    with urllib.request.urlopen(METADATA, timeout=60) as response:
        source = next(x for x in json.load(response) if x['ref'] == 'mlg-ulb/creditcardfraud')
    expected_license = 'Database: Open Database, Contents: Database Contents'
    if source['licenseName'] != expected_license:
        raise SystemExit('Publisher licence changed; manual source review required.')
    archive = raw / 'download.zip.part'
    try:
        with urllib.request.urlopen(URL, timeout=120) as response, archive.open('wb') as output:
            shutil.copyfileobj(response, output)
        with zipfile.ZipFile(archive) as bundle:
            member = bundle.getinfo('creditcard.csv')
            if member.file_size > 200_000_000:
                raise ValueError('Unexpected uncompressed size')
            with bundle.open(member) as src, target.with_suffix('.part').open('wb') as dst:
                shutil.copyfileobj(src, dst)
        with target.with_suffix('.part').open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if digest != EXPECTED_SHA256:
            raise ValueError('Downloaded bytes differ from accepted dataset; investigate before use')
        target.with_suffix('.part').replace(target)
        record = {
            'source': source['url'], 'owner': source['ownerName'],
            'license': source['licenseName'], 'requested_version': 3,
            'download_endpoint': URL, 'retrieved_at': datetime.now(timezone.utc).isoformat(),
            'filename': target.name, 'bytes': target.stat().st_size,
            'sha256': digest,
            'licence_urls': ['https://opendatacommons.org/licenses/odbl/1-0/',
                             'https://opendatacommons.org/licenses/dbcl/1-0/'],
        }
        Path('data/provenance').mkdir(parents=True, exist_ok=True)
        Path('data/provenance/source.json').write_text(json.dumps(record, indent=2) + '\n')
        print(json.dumps(record, indent=2))
    finally:
        archive.unlink(missing_ok=True)
        target.with_suffix('.part').unlink(missing_ok=True)


if __name__ == '__main__':
    main()
