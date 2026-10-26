import psycopg.errors
import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import ProgrammingError

from tests.support import insert_usage_event, new_agent


def test_default_workspace_exists(conn: Connection) -> None:
    names = conn.execute(text("SELECT name FROM workspaces")).scalars().all()
    assert "default" in names


def test_mock_prices_are_seeded(conn: Connection) -> None:
    models = (
        conn.execute(text("SELECT model FROM model_prices WHERE provider = 'mock' ORDER BY model"))
        .scalars()
        .all()
    )
    assert models == ["mock-large", "mock-small"]


def denied(conn: Connection, role: str, sql: str) -> None:
    """Verifie qu'une requete est refusee pour ce role, sans casser la transaction du test."""
    conn.execute(text(f"SET LOCAL ROLE {role}"))
    try:
        with pytest.raises(ProgrammingError) as error, conn.begin_nested():
            conn.execute(text(sql))
        assert isinstance(error.value.orig, psycopg.errors.InsufficientPrivilege)
    finally:
        conn.execute(text("RESET ROLE"))


def test_app_role_can_insert_but_not_change_or_delete_usage_events(conn: Connection) -> None:
    ids = new_agent(conn)
    insert_usage_event(conn, ids)
    conn.execute(text("SET LOCAL ROLE gateway_app"))
    insert_usage_event(conn, ids)
    conn.execute(text("RESET ROLE"))
    denied(conn, "gateway_app", "UPDATE usage_events SET cost_micro_usd = 0")
    denied(conn, "gateway_app", "DELETE FROM usage_events")


def test_app_role_cannot_physically_delete_agents(conn: Connection) -> None:
    new_agent(conn)
    denied(conn, "gateway_app", "DELETE FROM agents")


def test_purge_role_can_delete_but_not_update_usage_events(conn: Connection) -> None:
    ids = new_agent(conn)
    insert_usage_event(conn, ids)
    denied(conn, "gateway_purge", "UPDATE usage_events SET cost_micro_usd = 0")
    conn.execute(text("SET LOCAL ROLE gateway_purge"))
    conn.execute(text("DELETE FROM usage_events"))
    conn.execute(text("RESET ROLE"))
    assert conn.execute(text("SELECT count(*) FROM usage_events")).scalar_one() == 0
