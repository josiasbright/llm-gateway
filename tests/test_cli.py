import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.agents import AgentExistsError, create_agent
from app.cli import dollars, render_report


def test_dollars_shows_six_decimals() -> None:
    assert dollars(72) == "0.000072"
    assert dollars(0) == "0.000000"
    assert dollars(21_000_000) == "21.000000"


def test_creating_the_same_agent_twice_fails(migrated_engine: Engine) -> None:
    project = f"projet-{uuid.uuid4().hex[:8]}"
    with migrated_engine.begin() as conn:
        create_agent(conn, project, "bot")
    with pytest.raises(AgentExistsError), migrated_engine.begin() as conn:
        create_agent(conn, project, "bot")


def test_two_agents_can_share_a_project(migrated_engine: Engine) -> None:
    project = f"projet-{uuid.uuid4().hex[:8]}"
    with migrated_engine.begin() as conn:
        first = create_agent(conn, project, "bot-a")
        second = create_agent(conn, project, "bot-b")
    assert first != second


def test_agent_names_must_not_be_empty(migrated_engine: Engine) -> None:
    with pytest.raises(ValueError), migrated_engine.begin() as conn:
        create_agent(conn, "projet", "")


def test_report_lists_the_spending_of_an_agent(client: TestClient, migrated_engine: Engine) -> None:
    suffix = uuid.uuid4().hex[:8]
    with migrated_engine.begin() as conn:
        key = create_agent(conn, f"demo-{suffix}", f"support-{suffix}")
    body = {"model": "mock-small", "messages": [{"role": "user", "content": "un deux trois"}]}
    for _ in range(2):
        client.post("/v1/chat/completions", json=body, headers={"Authorization": f"Bearer {key}"})
    with migrated_engine.connect() as conn:
        report = render_report(conn, days=7)
    line = next(line for line in report.splitlines() if f"support-{suffix}" in line)
    # 2 appels, 6 tokens en entree, 14 en sortie, 34 micro-dollars.
    assert line.split()[-4:] == ["2", "6", "14", "0.000034"]
    assert "Total" in report
