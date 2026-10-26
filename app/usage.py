import uuid
from datetime import datetime

from sqlalchemy import Connection, text

from app.pricing import Price
from app.security import AgentIdentity


def record_event(
    conn: Connection,
    identity: AgentIdentity,
    request_id: uuid.UUID,
    occurred_at: datetime,
    provider: str,
    model: str,
    tokens_in: int,
    tokens_out: int,
    price: Price,
    cost_micro_usd: int,
    latency_ms: int,
) -> None:
    """Ecrit un evenement. Un meme request_id n'est jamais compte deux fois."""
    conn.execute(
        text(
            """
            INSERT INTO usage_events
                (id, request_id, occurred_at, workspace_id, project_id, agent_id,
                 provider, model, tokens_in, tokens_out,
                 price_in_micro_per_mtok, price_out_micro_per_mtok,
                 cost_micro_usd, latency_ms, status)
            VALUES
                (:id, :request_id, :occurred_at, :workspace_id, :project_id, :agent_id,
                 :provider, :model, :tokens_in, :tokens_out,
                 :price_in, :price_out, :cost, :latency_ms, 'success')
            ON CONFLICT (request_id) DO NOTHING
            """
        ),
        {
            "id": uuid.uuid4(),
            "request_id": request_id,
            "occurred_at": occurred_at,
            "workspace_id": identity.workspace_id,
            "project_id": identity.project_id,
            "agent_id": identity.agent_id,
            "provider": provider,
            "model": model,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "price_in": price.price_in_micro_per_mtok,
            "price_out": price.price_out_micro_per_mtok,
            "cost": cost_micro_usd,
            "latency_ms": latency_ms,
        },
    )
