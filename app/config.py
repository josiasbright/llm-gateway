"""Configuration minimale, lue dans l'environnement puis dans le fichier .env."""

import os
from pathlib import Path

from sqlalchemy.engine import URL, make_url

ROOT = Path(__file__).resolve().parent.parent


def read_env_file(path: Path) -> dict[str, str]:
    """Lit les lignes NOM=valeur d'un fichier .env, en ignorant vides et commentaires."""
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        name, _, value = line.partition("=")
        values[name.strip()] = value.strip()
    return values


def database_url() -> str:
    """Adresse de la base : variable d'environnement d'abord, sinon fichier .env."""
    url = os.environ.get("DATABASE_URL")
    env_path = ROOT / ".env"
    if not url and env_path.exists():
        url = read_env_file(env_path).get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL introuvable : copier .env.example en .env")
    return url


def sqlalchemy_url() -> URL:
    """Adresse de la base au format SQLAlchemy, avec le pilote psycopg 3."""
    return make_url(database_url()).set(drivername="postgresql+psycopg")
