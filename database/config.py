"""Direct URL locally or file-mounted password in Compose. Never log credentials."""

import os
from pathlib import Path

from sqlalchemy.engine import URL


def database_url():
    if os.getenv("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    password_file = os.getenv("DB_PASSWORD_FILE")
    if not password_file:
        return None
    password = Path(password_file).read_text().strip()
    if not password:
        raise ValueError("Empty database secret")
    return URL.create(
        "postgresql+psycopg",
        username=os.getenv("DB_USER", "fraud_owner"),
        password=password,
        host=os.getenv("DB_HOST", "db"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "fraud_demo"),
    )
