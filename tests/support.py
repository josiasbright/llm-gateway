import re
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.engine import URL

from app.config import ROOT, sqlalchemy_url

EXPECTED_TABLES = {
    "workspaces",
    "projects",
    "agents",
    "api_keys",
    "provider_credentials",
    "model_prices",
    "usage_events",
    "budgets",
    "budget_counters",
    "alerts",
    "admin_sessions",
}


def alembic_config(url: URL) -> Config:
    """Configuration Alembic qui vise une base precise, sans dependre du dossier courant."""
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", (ROOT / "migrations").as_posix())
    config.attributes["url"] = url
    return config


def upgrade_head(url: URL) -> None:
    command.upgrade(alembic_config(url), "head")


@contextmanager
def temporary_database(admin: Engine) -> Iterator[URL]:
    """Cree une base vide au nom aleatoire, et la supprime ensuite."""
    name = f"gateway_test_{uuid.uuid4().hex[:12]}"
    if not re.fullmatch(r"[a-z0-9_]+", name):
        raise ValueError("nom de base invalide")
    with admin.connect() as connection:
        connection.execute(text(f"CREATE DATABASE {name}"))
    try:
        yield sqlalchemy_url().set(database=name)
    finally:
        with admin.connect() as connection:
            connection.execute(text(f"DROP DATABASE IF EXISTS {name} WITH (FORCE)"))


def make_admin_engine() -> Engine:
    """Connexion a la base d'entretien, necessaire pour creer et supprimer des bases."""
    return create_engine(sqlalchemy_url().set(database="postgres"), isolation_level="AUTOCOMMIT")


def new_agent(connection: Connection) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """Insere un projet et un agent, et retourne (workspace, projet, agent)."""
    workspace_id = connection.execute(text("SELECT id FROM workspaces LIMIT 1")).scalar_one()
    project_id, agent_id = uuid.uuid4(), uuid.uuid4()
    connection.execute(
        text("INSERT INTO projects (id, workspace_id, name) VALUES (:id, :ws, :name)"),
        {"id": project_id, "ws": workspace_id, "name": f"projet-{project_id.hex[:8]}"},
    )
    connection.execute(
        text("INSERT INTO agents (id, project_id, name) VALUES (:id, :project, :name)"),
        {"id": agent_id, "project": project_id, "name": f"agent-{agent_id.hex[:8]}"},
    )
    return workspace_id, project_id, agent_id


def insert_usage_event(
    connection: Connection,
    ids: tuple[uuid.UUID, uuid.UUID, uuid.UUID],
    request_id: uuid.UUID | None = None,
    status: str = "success",
    cost: int = 100,
) -> uuid.UUID:
    """Insere un evenement d'usage et retourne son request_id."""
    workspace_id, project_id, agent_id = ids
    request_id = request_id or uuid.uuid4()
    connection.execute(
        text(
            """
            INSERT INTO usage_events
                (id, request_id, occurred_at, workspace_id, project_id, agent_id,
                 provider, model, status, cost_micro_usd)
            VALUES
                (:id, :request_id, now(), :ws, :project, :agent,
                 'mock', 'mock-small', :status, :cost)
            """
        ),
        {
            "id": uuid.uuid4(),
            "request_id": request_id,
            "ws": workspace_id,
            "project": project_id,
            "agent": agent_id,
            "status": status,
            "cost": cost,
        },
    )
    return request_id
