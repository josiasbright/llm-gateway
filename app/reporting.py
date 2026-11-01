from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import Connection, text

from app.pricing import MICRO


def dollars(micro_usd: int) -> str:
    """Affiche des micro-dollars en dollars, avec six decimales."""
    return f"{Decimal(micro_usd) / Decimal(MICRO):.6f}"


@dataclass(frozen=True)
class UsageRow:
    project: str
    agent: str
    calls: int
    tokens_in: int
    tokens_out: int
    cost_micro_usd: int


@dataclass(frozen=True)
class UsageReport:
    days: int
    rows: tuple[UsageRow, ...]
    uses_mock_prices: bool

    @property
    def total_calls(self) -> int:
        return sum(row.calls for row in self.rows)

    @property
    def total_tokens_in(self) -> int:
        return sum(row.tokens_in for row in self.rows)

    @property
    def total_tokens_out(self) -> int:
        return sum(row.tokens_out for row in self.rows)

    @property
    def total_cost_micro_usd(self) -> int:
        return sum(row.cost_micro_usd for row in self.rows)


def fetch_usage(conn: Connection, days: int) -> UsageReport:
    """Depenses par projet et par agent sur les derniers jours, du plus cher au moins cher."""
    rows = conn.execute(
        text(
            """
            SELECT p.name AS project, a.name AS agent, count(*) AS calls,
                   coalesce(sum(e.tokens_in), 0) AS tokens_in,
                   coalesce(sum(e.tokens_out), 0) AS tokens_out,
                   coalesce(sum(e.cost_micro_usd), 0) AS cost
            FROM usage_events e
            JOIN agents a ON a.id = e.agent_id
            JOIN projects p ON p.id = e.project_id
            WHERE e.occurred_at >= now() - (:days * interval '1 day')
            GROUP BY p.name, a.name
            ORDER BY sum(e.cost_micro_usd) DESC, a.name
            """
        ),
        {"days": days},
    ).all()
    uses_mock = conn.execute(
        text(
            """
            SELECT coalesce(bool_or(provider = 'mock'), false) FROM usage_events
            WHERE occurred_at >= now() - (:days * interval '1 day')
            """
        ),
        {"days": days},
    ).scalar_one()
    return UsageReport(
        days=days,
        rows=tuple(
            UsageRow(
                r.project, r.agent, int(r.calls), int(r.tokens_in), int(r.tokens_out), int(r.cost)
            )
            for r in rows
        ),
        uses_mock_prices=bool(uses_mock),
    )
