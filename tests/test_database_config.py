from sqlalchemy.engine import URL

from database.config import database_url


def test_secret_file_supports_special_characters_without_url_interpolation(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    secret = tmp_path / "password"
    secret.write_text("special@:/?password\n")
    monkeypatch.setenv("DB_PASSWORD_FILE", str(secret))
    monkeypatch.setenv("DB_HOST", "db")
    result = database_url()
    assert isinstance(result, URL)
    assert result.password == "special@:/?password"
    assert result.host == "db"
    assert result.password not in str(result)


def test_direct_url_takes_precedence(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://localhost/demo")
    monkeypatch.setenv("DB_PASSWORD_FILE", "/not/used")
    assert database_url() == "postgresql+psycopg://localhost/demo"


def test_no_configuration_is_explicit(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DB_PASSWORD_FILE", raising=False)
    assert database_url() is None
