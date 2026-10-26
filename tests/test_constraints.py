import uuid
from datetime import UTC, datetime

import psycopg.errors
import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from tests.support import insert_usage_event, new_agent


def assert_violation(error: pytest.ExceptionInfo[DBAPIError], kind: type[Exception]) -> None:
    assert isinstance(error.value.orig, kind), (
        f"attendu {kind.__name__}, obtenu {error.value.orig!r}"
    )


def insert_budget(
    connection: Connection,
    workspace_id: uuid.UUID,
    agent_id: uuid.UUID | None,
    project_id: uuid.UUID | None,
    period: str = "day",
    archived: bool = False,
) -> None:
    connection.execute(
        text(
            """
            INSERT INTO budgets
                (id, workspace_id, agent_id, project_id, period, limit_micro_usd,
                 alert_threshold_pct, action_at_limit, archived_at)
            VALUES
                (:id, :ws, :agent, :project, :period, 1000000, 80, 'block',
                 CASE WHEN :archived THEN now() END)
            """
        ),
        {
            "id": uuid.uuid4(),
            "ws": workspace_id,
            "agent": agent_id,
            "project": project_id,
            "period": period,
            "archived": archived,
        },
    )


def test_agent_status_must_be_known(conn: Connection) -> None:
    _, project_id, _ = new_agent(conn)
    with pytest.raises(IntegrityError) as error:
        conn.execute(
            text("INSERT INTO agents (id, project_id, name, status) VALUES (:i, :p, 'x', 'bogus')"),
            {"i": uuid.uuid4(), "p": project_id},
        )
    assert_violation(error, psycopg.errors.CheckViolation)


def test_budget_with_both_scopes_is_rejected(conn: Connection) -> None:
    ws, project_id, agent_id = new_agent(conn)
    with pytest.raises(IntegrityError) as error:
        insert_budget(conn, ws, agent_id, project_id)
    assert_violation(error, psycopg.errors.CheckViolation)


def test_budget_with_no_scope_is_rejected(conn: Connection) -> None:
    ws, _, _ = new_agent(conn)
    with pytest.raises(IntegrityError) as error:
        insert_budget(conn, ws, None, None)
    assert_violation(error, psycopg.errors.CheckViolation)


def test_budget_with_a_single_scope_is_accepted(conn: Connection) -> None:
    ws, project_id, agent_id = new_agent(conn)
    insert_budget(conn, ws, agent_id, None)
    insert_budget(conn, ws, None, project_id)


def test_only_one_active_budget_per_scope_and_period(conn: Connection) -> None:
    ws, _, agent_id = new_agent(conn)
    insert_budget(conn, ws, agent_id, None, period="day")
    insert_budget(conn, ws, agent_id, None, period="month")
    with pytest.raises(IntegrityError) as error:
        insert_budget(conn, ws, agent_id, None, period="day")
    assert_violation(error, psycopg.errors.UniqueViolation)


def test_archived_budget_does_not_block_a_new_one(conn: Connection) -> None:
    ws, _, agent_id = new_agent(conn)
    insert_budget(conn, ws, agent_id, None, archived=True)
    insert_budget(conn, ws, agent_id, None)


def insert_price(connection: Connection, model: str, start: str, end: str | None) -> None:
    connection.execute(
        text(
            """
            INSERT INTO model_prices
                (id, provider, model, price_in_micro_per_mtok, price_out_micro_per_mtok,
                 valid_from, valid_to)
            VALUES (:id, 'test', :model, 1, 2, :start, :end)
            """
        ),
        {
            "id": uuid.uuid4(),
            "model": model,
            "start": datetime.fromisoformat(start).replace(tzinfo=UTC),
            "end": datetime.fromisoformat(end).replace(tzinfo=UTC) if end else None,
        },
    )


def test_overlapping_prices_are_rejected(conn: Connection) -> None:
    insert_price(conn, "m1", "2026-01-01", "2026-06-01")
    with pytest.raises(IntegrityError) as error:
        insert_price(conn, "m1", "2026-03-01", None)
    assert_violation(error, psycopg.errors.ExclusionViolation)


def test_adjacent_prices_and_other_models_are_accepted(conn: Connection) -> None:
    insert_price(conn, "m2", "2026-01-01", "2026-06-01")
    insert_price(conn, "m2", "2026-06-01", None)
    insert_price(conn, "m3", "2026-03-01", None)


def test_price_end_must_be_after_start(conn: Connection) -> None:
    with pytest.raises(IntegrityError) as error:
        insert_price(conn, "m4", "2026-06-01", "2026-01-01")
    assert_violation(error, psycopg.errors.CheckViolation)


def test_usage_event_request_id_is_unique(conn: Connection) -> None:
    ids = new_agent(conn)
    request_id = insert_usage_event(conn, ids)
    with pytest.raises(IntegrityError) as error:
        insert_usage_event(conn, ids, request_id=request_id)
    assert_violation(error, psycopg.errors.UniqueViolation)


def test_usage_event_insert_can_be_repeated_without_double_counting(conn: Connection) -> None:
    ws, project_id, agent_id = new_agent(conn)
    request_id = uuid.uuid4()
    statement = text(
        """
        INSERT INTO usage_events
            (id, request_id, occurred_at, workspace_id, project_id, agent_id,
             provider, model, status)
        VALUES (:id, :request_id, now(), :ws, :project, :agent, 'mock', 'mock-small', 'success')
        ON CONFLICT (request_id) DO NOTHING
        """
    )
    for _ in range(2):
        conn.execute(
            statement,
            {
                "id": uuid.uuid4(),
                "request_id": request_id,
                "ws": ws,
                "project": project_id,
                "agent": agent_id,
            },
        )
    count = conn.execute(
        text("SELECT count(*) FROM usage_events WHERE request_id = :r"), {"r": request_id}
    ).scalar_one()
    assert count == 1


def test_usage_event_status_must_be_known(conn: Connection) -> None:
    with pytest.raises(IntegrityError) as error:
        insert_usage_event(conn, new_agent(conn), status="bogus")
    assert_violation(error, psycopg.errors.CheckViolation)


def test_usage_event_cost_cannot_be_negative(conn: Connection) -> None:
    with pytest.raises(IntegrityError) as error:
        insert_usage_event(conn, new_agent(conn), cost=-1)
    assert_violation(error, psycopg.errors.CheckViolation)


def test_alert_is_unique_per_budget_period_and_level(conn: Connection) -> None:
    ws, _, agent_id = new_agent(conn)
    insert_budget(conn, ws, agent_id, None)
    budget_id = conn.execute(
        text("SELECT id FROM budgets WHERE agent_id = :a"), {"a": agent_id}
    ).scalar_one()
    statement = text(
        "INSERT INTO alerts (id, budget_id, period_start, level) "
        "VALUES (:id, :b, '2026-10-01+00', 'threshold')"
    )
    conn.execute(statement, {"id": uuid.uuid4(), "b": budget_id})
    with pytest.raises(IntegrityError) as error:
        conn.execute(statement, {"id": uuid.uuid4(), "b": budget_id})
    assert_violation(error, psycopg.errors.UniqueViolation)
