import json
import logging

import joblib
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.main import ROOT, create_app
from api.schemas import TransactionInput
from api.services.inference import FEATURES, InferenceService

ARTIFACT = ROOT / "artifacts/model.joblib"
MANIFEST = ROOT / "docs/evidence/model-selection.json"
pytestmark = pytest.mark.skipif(
    not ARTIFACT.exists(), reason="Restore trusted model for integration tests"
)


def payload():
    return {
        "schema_version": "1",
        "source": "SYNTHETIC",
        "amount": 12.5,
        "time": 0.0,
        "v": [i / 100 for i in range(28)],
    }


def test_real_score_matches_direct_model_and_not_persisted():
    data = payload()
    frame = pd.DataFrame([[data["time"], *data["v"], data["amount"]]], columns=FEATURES)
    expected = float(joblib.load(ARTIFACT).predict_proba(frame)[0, 1])
    with TestClient(create_app()) as client:
        result = client.post("/score", json=data)
        assert result.status_code == 200
        assert result.json()["model_score"] == expected
        assert result.json()["persisted"] is False
        assert result.headers["X-Request-ID"]
        assert client.get("/model-info").json()["model_version"] == "ulb-v1"
        assert client.get("/health").json()["scoring_ready"] is True
        assert client.get("/ready").status_code == 503
        assert client.post("/predict", json=data).status_code == 503
        assert client.get("/predictions").status_code == 503


@pytest.mark.parametrize("change", ["hash", "features", "version", "threshold"])
def test_invalid_manifest_fails_closed(tmp_path, change):
    m = json.loads(MANIFEST.read_text())
    if change == "hash":
        m["model_sha256"] = "incorrect"
    elif change == "features":
        m["features"] = list(reversed(FEATURES))
    elif change == "version":
        m["sklearn"] = "wrong"
    else:
        m["threshold"] = 1.1
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(m))
    with TestClient(create_app(manifest=path)) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/health").json()["scoring_ready"] is False
        assert client.post("/score", json=payload()).status_code == 503


def test_missing_model_fails_closed(tmp_path):
    with TestClient(create_app(artifact=tmp_path / "missing")) as client:
        assert client.post("/score", json=payload()).status_code == 503


def test_feature_mapping_preserves_contract(monkeypatch):
    service = InferenceService(ARTIFACT, MANIFEST)
    data = TransactionInput(**payload())

    def capture(frame):
        assert frame.columns.tolist() == FEATURES
        assert frame.iloc[0].tolist() == [data.time, *data.v, data.amount]
        return np.array([[0.75, 0.25]])  # TEST DOUBLE, never a demonstration prediction.

    monkeypatch.setattr(service.model, "predict_proba", capture)
    assert service.score(data) == 0.25


def test_threshold_boundary_and_safe_inference_failure(monkeypatch):
    application = create_app()
    with TestClient(application) as client:
        service = application.state.inference
        monkeypatch.setattr(service, "score", lambda _: service.manifest["threshold"])
        result = client.post("/score", json=payload()).json()
        assert result["risk_category"] == "HIGH"
        assert result["decision"] == "FLAG_FOR_REVIEW"

        def fail(_):
            raise RuntimeError("private-path-secret")

        monkeypatch.setattr(service, "score", fail)
        response = client.post("/score", json=payload())
        assert response.status_code == 500
        assert "private-path-secret" not in response.text


def test_validation_does_not_echo_rejected_data_and_logs_are_minimal(caplog):
    with TestClient(create_app()) as client, caplog.at_level(logging.INFO, logger="fraud_api"):
        data = payload()
        data["amount"] = "PRIVATE_SECRET_VALUE"
        response = client.post("/score", json=data)
        assert response.status_code == 422
        assert "PRIVATE_SECRET_VALUE" not in response.text
        assert "PRIVATE_SECRET_VALUE" not in caplog.text
        records = [json.loads(r.message) for r in caplog.records if r.name == "fraud_api"]
        assert any(r.get("event") == "request" for r in records)
        assert all("body" not in r and "features" not in r for r in records)


def test_process_metrics_count_success_and_error():
    with TestClient(create_app()) as client:
        client.post("/score", json=payload())
        client.post("/score", json={})
        m = client.get("/metrics").json()
        assert m["score_requests"] == 1
        assert m["requests"] == 2
        assert m["errors"] == 1
        assert m["mean_scoring_ms"] >= 0
