"""Install revision 1 explicitly; API startup never creates tables."""

from database.config import database_url
from database.store import connect, install


def main():
    url = database_url()
    if url is None:
        raise ValueError("Database configuration required")
    engine = connect(url)
    try:
        install(engine)
        print("PostgreSQL schema revision 1 installed/verified")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
