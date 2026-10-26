import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection, Engine, create_engine
from sqlalchemy.engine import URL

from app.agents import create_agent
from app.db.session import get_engine
from app.main import app
from tests.support import (
    make_admin_engine,
    temporary_database,
    upgrade_head,
)


@pytest.fixture(scope="session")
def admin_engine() -> Iterator[Engine]:
    engine = make_admin_engine()
    yield engine
    engine.dispose()


@pytest.fixture
def empty_db_url(admin_engine: Engine) -> Iterator[URL]:
    """Une base vide, propre a un seul test."""
    with temporary_database(admin_engine) as url:
        yield url


@pytest.fixture(scope="session")
def migrated_engine(admin_engine: Engine) -> Iterator[Engine]:
    """Une base migree une seule fois pour tous les tests de contraintes."""
    with temporary_database(admin_engine) as url:
        upgrade_head(url)
        engine = create_engine(url)
        yield engine
        engine.dispose()


@pytest.fixture
def conn(migrated_engine: Engine) -> Iterator[Connection]:
    """Une connexion dont toutes les ecritures sont annulees a la fin du test."""
    with migrated_engine.connect() as connection:
        transaction = connection.begin()
        yield connection
        transaction.rollback()


@pytest.fixture
def client(migrated_engine: Engine) -> Iterator[TestClient]:
    """Un client du serveur branche sur la base de test."""
    app.dependency_overrides[get_engine] = lambda: migrated_engine
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def agent_key(migrated_engine: Engine) -> str:
    """Un agent neuf, avec sa cle d'API. Les donnees sont enregistrees pour de bon."""
    suffix = uuid.uuid4().hex[:8]
    with migrated_engine.begin() as connection:
        return create_agent(connection, f"projet-{suffix}", f"agent-{suffix}")
