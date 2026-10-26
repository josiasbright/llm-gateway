import pytest

from app.config import sqlalchemy_url


def test_sqlalchemy_url_uses_psycopg_driver(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:secret@127.0.0.1:15432/gateway")
    url = sqlalchemy_url()
    assert url.drivername == "postgresql+psycopg"
    assert (url.host, url.port, url.database) == ("127.0.0.1", 15432, "gateway")


def test_sqlalchemy_url_hides_password_when_printed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:secret@127.0.0.1:15432/gateway")
    assert "secret" not in str(sqlalchemy_url())
