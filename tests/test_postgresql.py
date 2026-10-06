"""Real PostgreSQL tests; dedicated disposable *_test database only."""

import os

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select, text
from sqlalchemy.engine import make_url

from api.main import ROOT, create_app
from database.store import Store, alerts, install, predictions, transactions

URL = os.getenv("FRAUD_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="Dedicated PostgreSQL test database required")


@pytest.fixture
def store():
    assert make_url(URL).database.endswith("_test"), "Refusing to clear non-test database"
    service = Store(URL)
    install(service.engine)
    with service.engine.begin() as conn:
        conn.execute(text("TRUNCATE alerts, predictions, transactions"))
    yield service
    service.engine.dispose()


def payload():
    return {
        "schema_version": "1",
        "source": "SYNTHETIC",
        "amount": 12.5,
        "time": 0.0,
        "v": [0.0] * 28,
    }


def counts(store):
    with store.engine.connect() as conn:
        return [
            conn.scalar(select(func.count()).select_from(t))
            for t in [transactions, predictions, alerts]
        ]


def high_payload(application):
    # SYNTHETIC out-of-distribution stress vector. Not realistic fraud evidence.
    coef = application.state.inference.model[-1].coef_[0]
    data = payload()
    data["v"] = (np.sign(coef[1:29]) * 1000).tolist()
    return data


def test_atomic_low_high_and_history(store):
    app = create_app(database_url=URL)
    with TestClient(app) as client:
        assert client.get("/ready").status_code == 200
        low = client.post("/predict", json=payload())
        assert low.status_code == 200
        assert low.json()["persisted"] is True
        assert low.json()["alert_id"] is None
        high = client.post("/predict", json=high_payload(app))
        assert high.status_code == 200
        assert high.json()["risk_category"] == "HIGH"
        assert high.json()["alert_id"] is not None
        assert counts(store) == [2, 2, 1]
        history = client.get("/predictions?limit=1").json()
        assert history["total"] == 2 and len(history["items"]) == 1
        assert history["items"][0]["id"] == high.json()["prediction_id"]
        assert client.get("/predictions?limit=101").status_code == 422
        assert client.get("/predictions?offset=-1").status_code == 422


def test_real_database_error_rolls_back_all_three_writes(store):
    app = create_app(database_url=URL)
    with TestClient(app) as client:
        engine = app.state.store.engine

        def reject_alert(conn, cursor, statement, parameters, context, executemany):
            if statement.startswith("INSERT INTO alerts"):
                cursor.execute("SELECT 1/0")  # Controlled PostgreSQL failure injection.

        event.listen(engine, "before_cursor_execute", reject_alert)
        try:
            response = client.post("/predict", json=high_payload(app))
            assert response.status_code == 503
            assert counts(store) == [0, 0, 0]
            assert "division" not in response.text
        finally:
            event.remove(engine, "before_cursor_execute", reject_alert)
        assert client.post("/predict", json=high_payload(app)).status_code == 200
        assert counts(store) == [1, 1, 1]


def test_api_restart_reads_same_record(store):
    with TestClient(create_app(database_url=URL)) as client:
        pid = client.post("/predict", json=payload()).json()["prediction_id"]
    with TestClient(create_app(database_url=URL)) as restarted:
        assert restarted.get("/predictions").json()["items"][0]["id"] == pid


def test_database_unavailable_returns_no_success():
    dead = "postgresql+psycopg://postgres@/missing?host=/tmp/fraud-nonexistent-socket&port=55432"
    with TestClient(create_app(database_url=dead)) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/ready").status_code == 503
        response = client.post("/predict", json=payload())
        assert response.status_code == 503
        assert "model_score" not in response.json()


def test_schema_revision_gate(store):
    with store.engine.begin() as conn:
        conn.execute(text("UPDATE schema_revision SET version=3"))
    try:
        with TestClient(create_app(database_url=URL)) as client:
            assert client.get("/ready").status_code == 503
    finally:
        with store.engine.begin() as conn:
            conn.execute(text("UPDATE schema_revision SET version=2"))


def test_analytics_empty_database(store):
    with TestClient(create_app(database_url=URL)) as client:
        result = client.get("/analytics").json()
        assert result["total_predictions"] == 0
        assert result["mean_model_score"] is None
        assert sum(b["count"] for b in result["score_bins"]) == 0
        assert client.get("/alerts").json()["items"] == []


def test_global_analytics_exceeds_history_page_and_alert_join(store):
    app = create_app(database_url=URL)
    with TestClient(app) as client:
        for _ in range(21):
            assert client.post("/predict", json=payload()).status_code == 200
        high = client.post("/predict", json=high_payload(app)).json()
        assert len(client.get("/predictions").json()["items"]) == 20
        result = client.get("/analytics").json()
        assert result["total_predictions"] == 22
        assert result["low_risk"] == 21 and result["high_risk"] == 1
        assert result["alerts"] == 1 and result["flagged_share"] == 1 / 22
        assert sum(b["count"] for b in result["score_bins"]) == 22
        assert sum(d["count"] for d in result["daily"]) == 22
        assert result["sources"] == {"SYNTHETIC": 22}
        alert = client.get("/alerts").json()["items"][0]
        assert alert["id"] == high["alert_id"] and alert["prediction_id"] == high["prediction_id"]
        assert alert["updated_at"] == alert["created_at"]
        assert alert["resolved_at"] is None
        assert client.get("/alerts?limit=101").status_code == 422
        assert client.get("/alerts?offset=-1").status_code == 422


def test_streamlit_form_with_real_http_and_database(store, monkeypatch):
    import subprocess
    import sys
    import time

    import httpx
    from streamlit.testing.v1 import AppTest

    environment = {**os.environ, "DATABASE_URL": URL}
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8768",
            "--no-access-log",
        ],
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    monkeypatch.setenv("API_BASE_URL", "http://127.0.0.1:8768")
    try:
        for _ in range(100):
            try:
                if httpx.get("http://127.0.0.1:8768/ready", timeout=1).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.1)
        else:
            raise AssertionError("Test API not ready")
        app = AppTest.from_file(ROOT / "dashboard/app.py", default_timeout=20).run()
        assert not app.exception
        assert app.metric[0].value == "0"
        next(b for b in app.button if b.label == "Score and save").click().run()
        assert not app.exception
        assert app.metric[0].value == "1"
        assert app.success
        assert counts(store) == [1, 1, 0]
        app.text_area[0].set_value("[]")
        next(b for b in app.button if b.label == "Score and save").click().run()
        assert app.error
        assert not app.success
        assert counts(store) == [1, 1, 0]
    finally:
        process.terminate()
        process.wait(timeout=10)


def test_streamlit_unavailable_api(monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("API_BASE_URL", "http://127.0.0.1:1")
    app = AppTest.from_file(ROOT / "dashboard/app.py", default_timeout=20).run()
    assert not app.exception
    assert app.error
    assert not app.metric

def test_alert_resolution_lifecycle_is_atomic_and_idempotent(store):
    app = create_app(database_url=URL)
    with TestClient(app) as client:
        created = client.post("/predict", json=high_payload(app)).json()

    alert_id = created["alert_id"]
    before = store.alert_history(20, 0)["items"][0]
    assert before["id"] == alert_id
    assert before["status"] == "OPEN"
    assert before["resolved_at"] is None

    resolved = store.resolve_alert(alert_id)
    assert resolved is not None
    assert resolved["id"] == alert_id
    assert resolved["status"] == "RESOLVED"
    assert resolved["resolved_at"] is not None
    assert resolved["updated_at"] == resolved["resolved_at"]
    assert resolved["updated_at"] >= resolved["created_at"]

    first_resolved_at = resolved["resolved_at"]

    again = store.resolve_alert(alert_id)
    assert again is not None
    assert again["status"] == "RESOLVED"
    assert again["resolved_at"] == first_resolved_at
    assert again["updated_at"] == first_resolved_at

    assert store.resolve_alert("00000000-0000-0000-0000-000000000000") is None


def test_resolve_alert_api_contract(store, monkeypatch):
    app = create_app(database_url=URL)
    with TestClient(app) as client:
        created = client.post("/predict", json=high_payload(app)).json()
        alert_id = created["alert_id"]

        resolved = client.post(f"/alerts/{alert_id}/resolve")
        assert resolved.status_code == 200
        body = resolved.json()
        assert body["id"] == alert_id
        assert body["status"] == "RESOLVED"
        assert body["resolved_at"] is not None
        assert body["updated_at"] == body["resolved_at"]

        first_resolved_at = body["resolved_at"]

        repeated = client.post(f"/alerts/{alert_id}/resolve")
        assert repeated.status_code == 200
        assert repeated.json()["resolved_at"] == first_resolved_at

        missing = client.post(
            "/alerts/00000000-0000-0000-0000-000000000000/resolve"
        )
        assert missing.status_code == 404
        assert missing.json() == {"detail": "Alert not found"}

        malformed = client.post("/alerts/not-a-uuid/resolve")
        assert malformed.status_code == 422

        def fail_resolution(alert_id):
            raise RuntimeError("controlled database failure")

        monkeypatch.setattr(app.state.store, "resolve_alert", fail_resolution)
        failed = client.post(f"/alerts/{alert_id}/resolve")
        assert failed.status_code == 503
        assert failed.json() == {"detail": "Alert could not be resolved"}
        assert "controlled database failure" not in failed.text

def test_alert_history_status_filter_applies_before_pagination(store):
    app = create_app(database_url=URL)
    with TestClient(app) as client:
        first = client.post("/predict", json=high_payload(app)).json()
        second = client.post("/predict", json=high_payload(app)).json()

        resolved = client.post(f"/alerts/{first['alert_id']}/resolve")
        assert resolved.status_code == 200

        all_alerts = client.get("/alerts?limit=1&offset=0")
        assert all_alerts.status_code == 200
        assert all_alerts.json()["total"] == 2
        assert len(all_alerts.json()["items"]) == 1

        open_alerts = client.get("/alerts?status=OPEN&limit=1&offset=0")
        assert open_alerts.status_code == 200
        assert open_alerts.json()["total"] == 1
        assert len(open_alerts.json()["items"]) == 1
        assert open_alerts.json()["items"][0]["id"] == second["alert_id"]
        assert open_alerts.json()["items"][0]["status"] == "OPEN"

        resolved_alerts = client.get("/alerts?status=RESOLVED&limit=1&offset=0")
        assert resolved_alerts.status_code == 200
        assert resolved_alerts.json()["total"] == 1
        assert len(resolved_alerts.json()["items"]) == 1
        assert resolved_alerts.json()["items"][0]["id"] == first["alert_id"]
        assert resolved_alerts.json()["items"][0]["status"] == "RESOLVED"

        invalid = client.get("/alerts?status=CLOSED")
        assert invalid.status_code == 422

def test_streamlit_review_queue_resolves_alert_through_http(store, monkeypatch):
    import subprocess
    import sys
    import time

    import httpx
    from streamlit.testing.v1 import AppTest

    api_app = create_app(database_url=URL)
    with TestClient(api_app) as client:
        created = client.post("/predict", json=high_payload(api_app)).json()
        alert_id = created["alert_id"]

    environment = {**os.environ, "DATABASE_URL": URL}
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8769",
            "--no-access-log",
        ],
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    monkeypatch.setenv("API_BASE_URL", "http://127.0.0.1:8769")

    try:
        for _ in range(100):
            try:
                if httpx.get("http://127.0.0.1:8769/ready", timeout=1).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.1)
        else:
            raise AssertionError("Test API not ready")

        app = AppTest.from_file(ROOT / "dashboard/app.py", default_timeout=20).run()
        assert not app.exception

        status_control = next(
            control for control in app.radio if control.label == "Alert status"
        )
        assert status_control.value == "OPEN"

        resolve = next(
            button for button in app.button
            if button.label == f"Resolve alert {alert_id}"
        )
        resolve.click().run()

        assert not app.exception

        with store.engine.connect() as conn:
            row = conn.execute(
                select(
                    alerts.c.status,
                    alerts.c.updated_at,
                    alerts.c.resolved_at,
                ).where(alerts.c.id == alert_id)
            ).one()

        assert row.status == "RESOLVED"
        assert row.resolved_at is not None
        assert row.updated_at == row.resolved_at

        app = next(
            control for control in app.radio if control.label == "Alert status"
        ).set_value("RESOLVED").run()

        assert not app.exception
        assert any(
            alert_id in str(dataframe.value)
            for dataframe in app.dataframe
        )
    finally:
        process.terminate()
        process.wait(timeout=10)
