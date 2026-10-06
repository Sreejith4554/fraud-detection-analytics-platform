"""Explicit, ordered PostgreSQL schema migrations."""

from sqlalchemy import inspect, select, text

from database.schema_version import LATEST_SCHEMA_REVISION
from database.store import revision


def current_revision(engine):
    """Return the installed schema revision, or None for an empty database."""
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "schema_revision" not in table_names:
        managed_tables = {"transactions", "predictions", "alerts"}
        existing_managed_tables = sorted(table_names & managed_tables)
        if existing_managed_tables:
            raise ValueError(
                "Managed tables exist without schema revision: "
                + ", ".join(existing_managed_tables)
            )
        return None

    with engine.connect() as conn:
        versions = conn.execute(select(revision.c.version)).scalars().all()

    if len(versions) != 1:
        raise ValueError("Invalid schema revision state")

    return versions[0]


def migrate_1_to_2(engine):
    """Add alert lifecycle timestamps while preserving revision-1 records."""
    with engine.begin() as conn:
        version = conn.execute(select(revision.c.version)).scalar_one()
        if version != 1:
            raise ValueError(f"Expected schema revision 1, found {version}")

        conn.execute(
            text(
                "ALTER TABLE alerts "
                "ADD COLUMN updated_at TIMESTAMPTZ, "
                "ADD COLUMN resolved_at TIMESTAMPTZ"
            )
        )
        conn.execute(text("UPDATE alerts SET updated_at = created_at"))
        conn.execute(text("ALTER TABLE alerts ALTER COLUMN updated_at SET NOT NULL"))
        conn.execute(text("UPDATE schema_revision SET version = 2"))


def migrate(engine):
    """Upgrade an installed schema to the latest supported revision."""
    version = current_revision(engine)

    if version is None:
        raise ValueError("Schema not installed")

    if version > LATEST_SCHEMA_REVISION:
        raise ValueError(
            f"Database schema revision {version} is newer than supported "
            f"revision {LATEST_SCHEMA_REVISION}"
        )

    if version < 1:
        raise ValueError(f"Unsupported schema revision {version}")

    if version == 1:
        migrate_1_to_2(engine)
        version = 2

    if version != LATEST_SCHEMA_REVISION:
        raise ValueError(f"Unsupported schema revision {version}")

    return version
