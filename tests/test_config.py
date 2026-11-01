import pytest

from app.config import admin_password, setting, sqlalchemy_url


def test_sqlalchemy_url_uses_psycopg_driver(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:secret@127.0.0.1:15432/gateway")
    url = sqlalchemy_url()
    assert url.drivername == "postgresql+psycopg"
    assert (url.host, url.port, url.database) == ("127.0.0.1", 15432, "gateway")


def test_sqlalchemy_url_hides_password_when_printed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:secret@127.0.0.1:15432/gateway")
    assert "secret" not in str(sqlalchemy_url())


def test_admin_password_is_read_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "un-vrai-mot-de-passe")
    assert admin_password() == "un-vrai-mot-de-passe"


def test_admin_password_is_off_when_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "")
    assert admin_password() is None


def test_admin_password_is_off_when_it_is_the_example_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "change-me-admin")
    assert admin_password() is None


def test_an_empty_environment_variable_wins_over_the_env_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("UN_REGLAGE_DE_TEST", "")
    assert setting("UN_REGLAGE_DE_TEST") == ""
