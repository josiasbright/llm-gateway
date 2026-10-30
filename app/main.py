import time
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Engine

from app import __version__
from app.db.session import get_engine
from app.errors import GatewayError
from app.pricing import compute_cost_micro_usd, find_price
from app.providers import provider_for_model
from app.providers.base import Message
from app.security import authenticate
from app.usage import record_event

app = FastAPI(title="LLM Gateway Auto Pilot", version=__version__)

EngineDep = Annotated[Engine, Depends(get_engine)]

# Declarer le schema de securite donne le bouton Authorize de la page /docs.
# Un simple parametre nomme Authorization serait ignore par OpenAPI, donc jamais envoye.
bearer_scheme = HTTPBearer(auto_error=False, description="Cle d'API d'un agent, de la forme gw_...")
CredentialsDep = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    model: str
    messages: list[ChatMessage] = Field(min_length=1)
    stream: bool = False


@app.exception_handler(GatewayError)
async def gateway_error_handler(request: Request, error: GatewayError) -> JSONResponse:
    headers = {"WWW-Authenticate": "Bearer"} if error.status_code == 401 else None
    return JSONResponse(status_code=error.status_code, content=error.body(), headers=headers)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/chat/completions")
def chat_completions(
    body: ChatRequest,
    response: Response,
    engine: EngineDep,
    credentials: CredentialsDep,
) -> dict[str, Any]:
    authorization = f"Bearer {credentials.credentials}" if credentials else None
    request_id = uuid.uuid4()
    response.headers["X-Request-ID"] = str(request_id)

    with engine.begin() as conn:
        identity = authenticate(conn, authorization)
        if body.stream:
            raise GatewayError(
                400, "Le streaming n'est pas encore pris en charge.", "stream_not_supported"
            )
        provider = provider_for_model(body.model)
        if provider is None:
            raise GatewayError(400, f"Modele inconnu : {body.model}.", "model_not_found")
        price = find_price(conn, provider.name, body.model, datetime.now(UTC))
        if price is None:
            raise GatewayError(
                500,
                f"Aucun prix configure pour le modele {body.model}.",
                "price_not_configured",
                "server_error",
            )

    # L'appel au fournisseur se fait sans garder de connexion a la base ouverte.
    started = time.perf_counter()
    completion = provider.complete(body.model, [Message(m.role, m.content) for m in body.messages])
    latency_ms = round((time.perf_counter() - started) * 1000)

    cost = compute_cost_micro_usd(completion.tokens_in, completion.tokens_out, price)
    with engine.begin() as conn:
        record_event(
            conn,
            identity,
            request_id,
            datetime.now(UTC),
            provider.name,
            body.model,
            completion.tokens_in,
            completion.tokens_out,
            price,
            cost,
            latency_ms,
        )

    return {
        "id": f"chatcmpl-{request_id.hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": body.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": completion.text},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": completion.tokens_in,
            "completion_tokens": completion.tokens_out,
            "total_tokens": completion.tokens_in + completion.tokens_out,
        },
    }
