import secrets
import time
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Query, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBasic,
    HTTPBasicCredentials,
    HTTPBearer,
)
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Engine

from app import __version__
from app.config import admin_password
from app.dashboard import render_dashboard
from app.db.session import get_engine
from app.errors import GatewayError
from app.pricing import compute_cost_micro_usd, find_price
from app.providers import provider_for_model
from app.providers.base import Message
from app.reporting import fetch_usage
from app.security import authenticate
from app.usage import record_event

app = FastAPI(title="LLM Gateway Auto Pilot", version=__version__)

EngineDep = Annotated[Engine, Depends(get_engine)]

# Declarer le schema de securite donne le bouton Authorize de la page /docs.
# Un simple parametre nomme Authorization serait ignore par OpenAPI, donc jamais envoye.
bearer_scheme = HTTPBearer(auto_error=False, description="Cle d'API d'un agent, de la forme gw_...")
CredentialsDep = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]

# Tableau de bord : un seul utilisateur, "admin", dont le mot de passe vient de ADMIN_PASSWORD.
basic_scheme = HTTPBasic(
    auto_error=False, description="Utilisateur admin, mot de passe ADMIN_PASSWORD"
)
BasicDep = Annotated[HTTPBasicCredentials | None, Depends(basic_scheme)]
DaysQuery = Annotated[int, Query(ge=1, le=365)]

PAGE_HEADERS = {
    "Cache-Control": "no-store",
    "Content-Security-Policy": (
        "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; "
        "form-action 'none'; frame-ancestors 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}


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
    headers = error.headers
    if headers is None and error.status_code == 401:
        headers = {"WWW-Authenticate": "Bearer"}
    return JSONResponse(status_code=error.status_code, content=error.body(), headers=headers)


def require_admin(credentials: BasicDep) -> None:
    """Refuse l'acces sans le bon mot de passe. Sans ADMIN_PASSWORD, tout reste ferme."""
    expected = admin_password()
    if expected is None:
        raise GatewayError(
            503,
            "Tableau de bord desactive : ADMIN_PASSWORD n'est pas configure.",
            "dashboard_disabled",
            "server_error",
        )
    valid = (
        credentials is not None
        and secrets.compare_digest(credentials.username.encode(), b"admin")
        and secrets.compare_digest(credentials.password.encode(), expected.encode())
    )
    if not valid:
        raise GatewayError(
            401,
            "Identifiants invalides. Utilisateur : admin.",
            "invalid_credentials",
            "authentication_error",
            headers={"WWW-Authenticate": 'Basic charset="UTF-8"'},
        )


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


@app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
def dashboard(
    engine: EngineDep, _admin: Annotated[None, Depends(require_admin)], days: DaysQuery = 7
) -> HTMLResponse:
    with engine.connect() as conn:
        report = fetch_usage(conn, days)
    return HTMLResponse(render_dashboard(report), headers=PAGE_HEADERS)


@app.get("/api/usage")
def api_usage(
    engine: EngineDep, _admin: Annotated[None, Depends(require_admin)], days: DaysQuery = 7
) -> dict[str, Any]:
    with engine.connect() as conn:
        report = fetch_usage(conn, days)
    return {
        "days": report.days,
        "uses_mock_prices": report.uses_mock_prices,
        "rows": [
            {
                "project": row.project,
                "agent": row.agent,
                "calls": row.calls,
                "tokens_in": row.tokens_in,
                "tokens_out": row.tokens_out,
                "cost_micro_usd": row.cost_micro_usd,
            }
            for row in report.rows
        ],
        "total": {
            "calls": report.total_calls,
            "tokens_in": report.total_tokens_in,
            "tokens_out": report.total_tokens_out,
            "cost_micro_usd": report.total_cost_micro_usd,
        },
    }
