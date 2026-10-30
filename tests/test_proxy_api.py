import hashlib

from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

BODY = {"model": "mock-small", "messages": [{"role": "user", "content": "un deux trois"}]}


def auth(key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {key}"}


def count_events(engine: Engine, key: str) -> int:
    key_hash = hashlib.sha256(key.encode()).digest()
    with engine.connect() as conn:
        return int(
            conn.execute(
                text(
                    """
                    SELECT count(*) FROM usage_events e
                    JOIN api_keys k ON k.agent_id = e.agent_id
                    WHERE k.key_hash = :h
                    """
                ),
                {"h": key_hash},
            ).scalar_one()
        )


def test_healthz(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_missing_key_is_rejected(client: TestClient) -> None:
    response = client.post("/v1/chat/completions", json=BODY)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_api_key"
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_unknown_key_is_rejected(client: TestClient) -> None:
    response = client.post("/v1/chat/completions", json=BODY, headers=auth("gw_inconnue"))
    assert response.status_code == 401


def test_chat_completion_has_the_openai_shape(client: TestClient, agent_key: str) -> None:
    response = client.post("/v1/chat/completions", json=BODY, headers=auth(agent_key))
    assert response.status_code == 200
    data = response.json()
    assert data["object"] == "chat.completion"
    assert data["model"] == "mock-small"
    assert data["choices"][0]["message"]["role"] == "assistant"
    assert data["usage"] == {"prompt_tokens": 3, "completion_tokens": 7, "total_tokens": 10}
    assert response.headers["X-Request-ID"]


def test_the_call_is_recorded_with_its_cost(
    client: TestClient, agent_key: str, migrated_engine: Engine
) -> None:
    client.post("/v1/chat/completions", json=BODY, headers=auth(agent_key))
    key_hash = hashlib.sha256(agent_key.encode()).digest()
    with migrated_engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT e.provider, e.model, e.tokens_in, e.tokens_out, e.cost_micro_usd,
                       e.price_in_micro_per_mtok, e.price_out_micro_per_mtok, e.status
                FROM usage_events e JOIN api_keys k ON k.agent_id = e.agent_id
                WHERE k.key_hash = :h
                """
            ),
            {"h": key_hash},
        ).one()
    # 3 tokens a 1 $ le million + 7 tokens a 2 $ le million = 17 micro-dollars.
    assert tuple(row) == ("mock", "mock-small", 3, 7, 17, 1_000_000, 2_000_000, "success")


def test_each_call_adds_one_event(
    client: TestClient, agent_key: str, migrated_engine: Engine
) -> None:
    for _ in range(3):
        client.post("/v1/chat/completions", json=BODY, headers=auth(agent_key))
    assert count_events(migrated_engine, agent_key) == 3


def test_unknown_model_is_rejected_without_recording(
    client: TestClient, agent_key: str, migrated_engine: Engine
) -> None:
    body = {**BODY, "model": "inconnu"}
    response = client.post("/v1/chat/completions", json=body, headers=auth(agent_key))
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "model_not_found"
    assert count_events(migrated_engine, agent_key) == 0


def test_revoked_key_is_rejected(
    client: TestClient, agent_key: str, migrated_engine: Engine
) -> None:
    key_hash = hashlib.sha256(agent_key.encode()).digest()
    with migrated_engine.begin() as conn:
        conn.execute(
            text("UPDATE api_keys SET revoked_at = now() WHERE key_hash = :h"), {"h": key_hash}
        )
    response = client.post("/v1/chat/completions", json=BODY, headers=auth(agent_key))
    assert response.status_code == 401


def test_disabled_agent_is_forbidden(
    client: TestClient, agent_key: str, migrated_engine: Engine
) -> None:
    key_hash = hashlib.sha256(agent_key.encode()).digest()
    with migrated_engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE agents SET status = 'disabled'
                WHERE id = (SELECT agent_id FROM api_keys WHERE key_hash = :h)
                """
            ),
            {"h": key_hash},
        )
    response = client.post("/v1/chat/completions", json=BODY, headers=auth(agent_key))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "agent_disabled"


def test_streaming_is_not_supported_yet(client: TestClient, agent_key: str) -> None:
    response = client.post(
        "/v1/chat/completions", json={**BODY, "stream": True}, headers=auth(agent_key)
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "stream_not_supported"


def test_empty_messages_are_rejected(client: TestClient, agent_key: str) -> None:
    body = {"model": "mock-small", "messages": []}
    response = client.post("/v1/chat/completions", json=body, headers=auth(agent_key))
    assert response.status_code == 422


def test_docs_offer_a_bearer_authorization(client: TestClient) -> None:
    schemes = client.get("/openapi.json").json()["components"]["securitySchemes"]
    assert any(s["type"] == "http" and s["scheme"] == "bearer" for s in schemes.values())


def test_authorization_is_not_a_plain_header_parameter(client: TestClient) -> None:
    route = client.get("/openapi.json").json()["paths"]["/v1/chat/completions"]["post"]
    assert all(p["name"].lower() != "authorization" for p in route.get("parameters", []))
