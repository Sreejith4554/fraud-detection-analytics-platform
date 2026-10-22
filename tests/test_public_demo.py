"""Public demonstration API access restrictions."""

from fastapi.testclient import TestClient
from api.main import create_app


def test_demo_blocks_prediction_writes(monkeypatch):
    monkeypatch.setenv("PUBLIC_DEMO_MODE", "1")
    with TestClient(create_app(database_url="")) as client:
        response = client.post("/predict", json={})
        assert response.status_code == 403


import pytest


@pytest.mark.parametrize("method,path", [("POST", "/score"), ("POST", "/predict"), ("POST", "/alerts/00000000-0000-0000-0000-000000000000/resolve"), ("POST", "/alerts/00000000-0000-0000-0000-000000000000/investigation"), ("POST", "/investigations/00000000-0000-0000-0000-000000000000/notes"), ("POST", "/investigations/00000000-0000-0000-0000-000000000000/close"), ("GET", "/metrics"), ("GET", "/docs"), ("GET", "/openapi.json"), ("GET", "/investigations/anything/notes")])
def test_demo_rejects_restricted_routes(monkeypatch, method, path):
    monkeypatch.setenv("PUBLIC_DEMO_MODE", "1")
    with TestClient(create_app(database_url="")) as client:
        assert client.request(method, path).status_code == 403


@pytest.mark.parametrize("path", ["/health", "/ready", "/model-info", "/predictions", "/analytics", "/alerts", "/alerts/00000000-0000-0000-0000-000000000000/investigation", "/investigations/00000000-0000-0000-0000-000000000000"])
def test_demo_allows_read_only_routes(monkeypatch, path):
    monkeypatch.setenv("PUBLIC_DEMO_MODE", "1")
    with TestClient(create_app(database_url="")) as client:
        assert client.get(path).status_code != 403
