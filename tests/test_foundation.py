import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def payload():
    return {"schema_version": "1", "source": "SYNTHETIC", "amount": 12.5,
            "time": 0, "v": [0.0] * 28}


def test_liveness_does_not_claim_readiness():
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['release'] == '1.1.0'
    assert response.json()['readiness_endpoint'] == '/ready'
    assert client.get('/ready').status_code == 503


@pytest.mark.parametrize('endpoint', ['/model-info', '/predictions'])
def test_unimplemented_dependencies_fail_closed(endpoint):
    assert client.get(endpoint).status_code == 503


def test_valid_request_has_no_fake_probability():
    result = client.post('/predict', json=payload())
    assert result.status_code == 503
    assert 'fraud_probability' not in result.json()


@pytest.mark.parametrize('field,value', [
    ('amount', -1), ('time', -1), ('v', [0.0] * 27), ('v', [0.0] * 29),
    ('schema_version', '2'), ('source', 'REAL_BANK'), ('Class', 1),
    ('amount', '12.5'), ('v', [True] * 28), ('amount', True),
])
def test_invalid_contract_rejected(field, value):
    data = payload()
    data[field] = value
    assert client.post('/predict', json=data).status_code == 422


def test_missing_feature_rejected():
    data = payload()
    del data['v']
    assert client.post('/predict', json=data).status_code == 422


def test_nonfinite_values_rejected_by_schema():
    from pydantic import ValidationError

    from api.schemas import TransactionInput
    for value in [float('nan'), float('inf'), float('-inf')]:
        data = payload()
        data['v'][0] = value
        with pytest.raises(ValidationError):
            TransactionInput(**data)


def test_openapi_exposes_contract():
    spec = client.get('/openapi.json').json()
    assert spec['info']['version'] == '1.1.0'
    assert '/predict' in spec['paths']
    assert spec['components']['schemas']['TransactionInput']['additionalProperties'] is False
