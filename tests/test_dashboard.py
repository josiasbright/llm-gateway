import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.agents import create_agent

BODY = {"model": "mock-small", "messages": [{"role": "user", "content": "un deux trois"}]}
GOOD = ("admin", "mot-de-passe-de-test")


@pytest.fixture(autouse=True)
def admin_password_is_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", GOOD[1])


def make_agent_with_calls(client: TestClient, engine: Engine, agent: str, calls: int) -> None:
    with engine.begin() as conn:
        key = create_agent(conn, f"projet-{uuid.uuid4().hex[:8]}", agent)
    for _ in range(calls):
        client.post("/v1/chat/completions", json=BODY, headers={"Authorization": f"Bearer {key}"})


def test_dashboard_is_closed_without_a_configured_password(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "")
    response = client.get("/dashboard", auth=GOOD)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "dashboard_disabled"


def test_dashboard_is_closed_with_the_example_password(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "change-me-admin")
    response = client.get("/dashboard", auth=("admin", "change-me-admin"))
    assert response.status_code == 503


def test_dashboard_asks_for_credentials(client: TestClient) -> None:
    response = client.get("/dashboard")
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"].startswith("Basic")


def test_dashboard_rejects_a_wrong_password(client: TestClient) -> None:
    assert client.get("/dashboard", auth=("admin", "faux")).status_code == 401


def test_dashboard_rejects_a_wrong_user(client: TestClient) -> None:
    assert client.get("/dashboard", auth=("autre", GOOD[1])).status_code == 401


def test_dashboard_shows_the_spending_of_an_agent(
    client: TestClient, migrated_engine: Engine
) -> None:
    agent = f"agent-{uuid.uuid4().hex[:8]}"
    make_agent_with_calls(client, migrated_engine, agent, calls=2)
    response = client.get("/dashboard?days=7", auth=GOOD)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert agent in response.text
    assert "0.000034" in response.text
    assert "prix fictifs" in response.text


def test_dashboard_escapes_names(client: TestClient, migrated_engine: Engine) -> None:
    agent = f"<b>gras</b>-{uuid.uuid4().hex[:6]}"
    make_agent_with_calls(client, migrated_engine, agent, calls=1)
    html = client.get("/dashboard", auth=GOOD).text
    assert "&lt;b&gt;gras&lt;/b&gt;" in html
    assert "<b>gras</b>" not in html


def test_dashboard_sets_protective_headers(client: TestClient) -> None:
    response = client.get("/dashboard", auth=GOOD)
    assert response.headers["Cache-Control"] == "no-store"
    assert "default-src 'none'" in response.headers["Content-Security-Policy"]
    assert response.headers["X-Content-Type-Options"] == "nosniff"


@pytest.mark.parametrize("days", ["0", "366", "abc"])
def test_dashboard_rejects_invalid_periods(client: TestClient, days: str) -> None:
    assert client.get(f"/dashboard?days={days}", auth=GOOD).status_code == 422


def test_dashboard_is_not_listed_in_the_public_docs(client: TestClient) -> None:
    assert "/dashboard" not in client.get("/openapi.json").json()["paths"]


def test_usage_api_requires_credentials(client: TestClient) -> None:
    assert client.get("/api/usage").status_code == 401


def test_usage_api_returns_rows_and_totals(client: TestClient, migrated_engine: Engine) -> None:
    agent = f"agent-{uuid.uuid4().hex[:8]}"
    make_agent_with_calls(client, migrated_engine, agent, calls=2)
    data = client.get("/api/usage?days=7", auth=GOOD).json()
    row = next(r for r in data["rows"] if r["agent"] == agent)
    assert (row["calls"], row["tokens_in"], row["tokens_out"], row["cost_micro_usd"]) == (
        2,
        6,
        14,
        34,
    )
    assert data["total"]["calls"] == sum(r["calls"] for r in data["rows"])
    assert data["uses_mock_prices"] is True
