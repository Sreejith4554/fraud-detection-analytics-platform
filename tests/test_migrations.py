"""PostgreSQL schema migration tests; dedicated disposable *_test database only."""

import os
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import event, inspect, select, text
from sqlalchemy.engine import make_url

from database.migrations import (
    LATEST_SCHEMA_REVISION,
    current_revision,
    migrate,
)
from database.store import (
    alerts,
    connect,
    install,
    predictions,
    revision,
    transactions,
    verify_schema,
)

URL = os.getenv("FRAUD_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not URL, reason="Dedicated PostgreSQL test database required"
)


@pytest.fixture
def engine():
    assert make_url(URL).database.endswith("_test"), "Refusing to alter non-test database"

    service_engine = connect(URL)

    with service_engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS alerts CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS predictions CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS transactions CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS schema_revision CASCADE"))

    yield service_engine

    with service_engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS alerts CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS predictions CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS transactions CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS schema_revision CASCADE"))

    install(service_engine)
    service_engine.dispose()


def test_fresh_install_creates_latest_revision(engine):
    assert current_revision(engine) is None

    install(engine)

    assert current_revision(engine) == LATEST_SCHEMA_REVISION
    columns = {column["name"] for column in inspect(engine).get_columns("alerts")}
    assert {"updated_at", "resolved_at"} <= columns



def test_managed_tables_without_revision_are_rejected(engine):
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE transactions ("
                "id UUID PRIMARY KEY"
                ")"
            )
        )

    with pytest.raises(
        ValueError,
        match="Managed tables exist without schema revision: transactions",
    ):
        current_revision(engine)


def test_revision_1_migrates_to_2_and_preserves_alert(engine):
    install(engine)

    transaction_id = uuid4()
    prediction_id = uuid4()
    alert_id = uuid4()
    created_at = datetime.now(timezone.utc)

    with engine.begin() as conn:
        conn.execute(
            transactions.insert().values(
                id=transaction_id,
                source="SYNTHETIC",
                schema_version="1",
                amount=12.5,
                elapsed_seconds=0.0,
                components=[0.0] * 28,
                created_at=created_at,
            )
        )
        conn.execute(
            predictions.insert().values(
                id=prediction_id,
                transaction_id=transaction_id,
                model_score=1.0,
                threshold=0.5,
                risk_category="HIGH",
                decision="FLAG_FOR_REVIEW",
                model_version="migration-test",
                model_sha256="0" * 64,
                created_at=created_at,
            )
        )
        conn.execute(
            alerts.insert().values(
                id=alert_id,
                prediction_id=prediction_id,
                status="OPEN",
                created_at=created_at,
                updated_at=created_at,
            )
        )

        conn.execute(text("ALTER TABLE alerts DROP COLUMN resolved_at"))
        conn.execute(text("ALTER TABLE alerts DROP COLUMN updated_at"))
        conn.execute(text("UPDATE schema_revision SET version = 1"))

    assert current_revision(engine) == 1

    assert migrate(engine) == 2
    assert current_revision(engine) == 2

    columns = {column["name"] for column in inspect(engine).get_columns("alerts")}
    assert {"updated_at", "resolved_at"} <= columns

    with engine.connect() as conn:
        row = conn.execute(
            select(
                alerts.c.id,
                alerts.c.prediction_id,
                alerts.c.status,
                alerts.c.created_at,
                alerts.c.updated_at,
                alerts.c.resolved_at,
            ).where(alerts.c.id == alert_id)
        ).one()

    assert row.id == alert_id
    assert row.prediction_id == prediction_id
    assert row.status == "OPEN"
    assert row.updated_at == row.created_at
    assert row.resolved_at is None


def test_revision_2_with_missing_required_column_is_rejected(engine):
    install(engine)

    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE alerts DROP COLUMN updated_at"))

    assert current_revision(engine) == 2

    with pytest.raises(Exception):
        verify_schema(engine)


def test_revision_2_migration_is_idempotent(engine):
    install(engine)

    assert migrate(engine) == 2
    assert migrate(engine) == 2
    assert current_revision(engine) == 2


def test_future_revision_is_rejected(engine):
    install(engine)

    with engine.begin() as conn:
        conn.execute(text("UPDATE schema_revision SET version = 3"))

    with pytest.raises(ValueError, match="newer than supported"):
        migrate(engine)

    assert current_revision(engine) == 3


def test_failed_revision_1_migration_rolls_back_schema_and_revision(engine):
    install(engine)

    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE alerts DROP COLUMN resolved_at"))
        conn.execute(text("ALTER TABLE alerts DROP COLUMN updated_at"))
        conn.execute(text("UPDATE schema_revision SET version = 1"))

    def fail_before_revision_advance(
        conn, cursor, statement, parameters, context, executemany
    ):
        if "UPDATE schema_revision SET version = 2" in statement:
            raise RuntimeError("controlled migration failure")

    event.listen(engine, "before_cursor_execute", fail_before_revision_advance)
    try:
        with pytest.raises(RuntimeError, match="controlled migration failure"):
            migrate(engine)
    finally:
        event.remove(engine, "before_cursor_execute", fail_before_revision_advance)

    assert current_revision(engine) == 1

    columns = {column["name"] for column in inspect(engine).get_columns("alerts")}
    assert "updated_at" not in columns
    assert "resolved_at" not in columns
