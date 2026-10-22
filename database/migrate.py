
"""Explicitly install or migrate PostgreSQL to the latest supported schema."""

import os

from sqlalchemy import text

from database.config import database_url
from database.migrations import current_revision, migrate
from database.schema_version import LATEST_SCHEMA_REVISION
from database.store import connect, install, verify_schema


def main():
    url = database_url()
    if url is None:
        raise ValueError("Database configuration required")

    engine = connect(url)
    try:
        # Refuse to migrate any database other than the isolated public demo.
        # Check the actual PostgreSQL connection before creating or changing tables.
        if os.getenv("PUBLIC_DEMO_DATABASE") == "1":
            with engine.connect() as conn:
                actual_database = conn.execute(
                    text("SELECT current_database()")
                ).scalar_one()

            if actual_database != "fraud_public_demo":
                raise ValueError(
                    "Public demo migration refused: unexpected database"
                )

        version = current_revision(engine)

        if version is None:
            install(engine)
        else:
            migrate(engine)

        final_version = current_revision(engine)
        if final_version != LATEST_SCHEMA_REVISION:
            raise ValueError(
                f"Schema migration incomplete: expected revision "
                f"{LATEST_SCHEMA_REVISION}, found {final_version}"
            )

        verify_schema(engine)
        print(f"PostgreSQL schema revision {final_version} installed/verified")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
