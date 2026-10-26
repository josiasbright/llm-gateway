import psycopg

from app.config import database_url


def test_database_accepts_connection_with_password() -> None:
    with psycopg.connect(database_url(), connect_timeout=5) as connection:
        row = connection.execute("select 1").fetchone()
    assert row == (1,)
