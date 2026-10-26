import uuid

from sqlalchemy import Connection, text

from app.security import generate_key, hash_key, visible_prefix


class AgentExistsError(Exception):
    """Un agent de ce nom existe deja dans ce projet."""


def _check_name(kind: str, name: str) -> None:
    if not 1 <= len(name) <= 80:
        raise ValueError(f"Le nom du {kind} doit faire de 1 a 80 caracteres.")


def create_agent(conn: Connection, project_name: str, agent_name: str) -> str:
    """Cree le projet si besoin, l'agent et une cle. Retourne la cle, a n'afficher qu'une fois."""
    _check_name("projet", project_name)
    _check_name("agent", agent_name)
    workspace_id = conn.execute(
        text("SELECT id FROM workspaces ORDER BY created_at, id LIMIT 1")
    ).scalar_one()
    project_id = conn.execute(
        text(
            """
            INSERT INTO projects (id, workspace_id, name) VALUES (:id, :workspace_id, :name)
            ON CONFLICT (workspace_id, name) DO UPDATE SET name = EXCLUDED.name
            RETURNING id
            """
        ),
        {"id": uuid.uuid4(), "workspace_id": workspace_id, "name": project_name},
    ).scalar_one()
    exists = conn.execute(
        text("SELECT 1 FROM agents WHERE project_id = :project_id AND name = :name"),
        {"project_id": project_id, "name": agent_name},
    ).first()
    if exists:
        raise AgentExistsError(agent_name)
    agent_id = uuid.uuid4()
    conn.execute(
        text("INSERT INTO agents (id, project_id, name) VALUES (:id, :project_id, :name)"),
        {"id": agent_id, "project_id": project_id, "name": agent_name},
    )
    key = generate_key()
    conn.execute(
        text(
            """
            INSERT INTO api_keys (id, agent_id, key_prefix, key_hash)
            VALUES (:id, :agent_id, :prefix, :key_hash)
            """
        ),
        {
            "id": uuid.uuid4(),
            "agent_id": agent_id,
            "prefix": visible_prefix(key),
            "key_hash": hash_key(key),
        },
    )
    return key
