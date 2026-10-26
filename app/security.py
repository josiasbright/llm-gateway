import hashlib
import secrets
import uuid
from dataclasses import dataclass

from sqlalchemy import Connection, text

from app.errors import GatewayError

KEY_PREFIX = "gw_"


def generate_key() -> str:
    return KEY_PREFIX + secrets.token_urlsafe(32)


def hash_key(key: str) -> bytes:
    """Seule l'empreinte est stockee en base : la cle elle-meme n'y est jamais ecrite."""
    return hashlib.sha256(key.encode("utf-8")).digest()


def visible_prefix(key: str) -> str:
    return key[:8]


@dataclass(frozen=True)
class AgentIdentity:
    agent_id: uuid.UUID
    project_id: uuid.UUID
    workspace_id: uuid.UUID


def bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def _invalid_key() -> GatewayError:
    return GatewayError(
        401,
        "Cle d'API absente ou invalide. Envoyer l'en-tete Authorization: Bearer <cle>.",
        "invalid_api_key",
        "authentication_error",
    )


def authenticate(conn: Connection, authorization: str | None) -> AgentIdentity:
    token = bearer_token(authorization)
    if token is None:
        raise _invalid_key()
    key_hash = hash_key(token)
    row = conn.execute(
        text(
            """
            SELECT a.id AS agent_id, a.project_id, p.workspace_id, a.status, k.revoked_at
            FROM api_keys k
            JOIN agents a ON a.id = k.agent_id
            JOIN projects p ON p.id = a.project_id
            WHERE k.key_hash = :key_hash
            """
        ),
        {"key_hash": key_hash},
    ).one_or_none()
    if row is None or row.revoked_at is not None:
        raise _invalid_key()
    if row.status != "active":
        raise GatewayError(403, "Cet agent est desactive.", "agent_disabled", "permission_error")
    conn.execute(
        text(
            """
            UPDATE api_keys SET last_used_at = now()
            WHERE key_hash = :key_hash
              AND (last_used_at IS NULL OR last_used_at < now() - interval '1 minute')
            """
        ),
        {"key_hash": key_hash},
    )
    return AgentIdentity(row.agent_id, row.project_id, row.workspace_id)
