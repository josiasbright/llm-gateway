import uuid

from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.agents import create_agent
from app.reporting import dollars, fetch_usage

BODY = {"model": "mock-small", "messages": [{"role": "user", "content": "un deux trois"}]}


def test_dollars_shows_six_decimals() -> None:
    assert dollars(72) == "0.000072"
    assert dollars(0) == "0.000000"
    assert dollars(21_000_000) == "21.000000"


def test_report_totals_match_the_rows(client: TestClient, migrated_engine: Engine) -> None:
    suffix = uuid.uuid4().hex[:8]
    with migrated_engine.begin() as conn:
        key = create_agent(conn, f"rapport-{suffix}", f"agent-{suffix}")
    for _ in range(3):
        client.post("/v1/chat/completions", json=BODY, headers={"Authorization": f"Bearer {key}"})
    with migrated_engine.connect() as conn:
        report = fetch_usage(conn, days=7)
    row = next(r for r in report.rows if r.agent == f"agent-{suffix}")
    # 3 appels de 3 tokens en entree, 7 en sortie, 17 micro-dollars chacun.
    assert (row.calls, row.tokens_in, row.tokens_out, row.cost_micro_usd) == (3, 9, 21, 51)
    assert report.total_calls == sum(r.calls for r in report.rows)
    assert report.total_cost_micro_usd == sum(r.cost_micro_usd for r in report.rows)
    assert report.uses_mock_prices is True


def test_report_is_sorted_from_the_most_expensive(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as conn:
        costs = [r.cost_micro_usd for r in fetch_usage(conn, days=7).rows]
    assert costs == sorted(costs, reverse=True)
