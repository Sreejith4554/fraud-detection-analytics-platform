"""Explicitly install or migrate PostgreSQL to the latest supported schema."""

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
