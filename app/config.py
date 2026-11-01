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


ADMIN_EXAMPLE_VALUE = "change-me-admin"


def setting(name: str) -> str | None:
    """Valeur d'un reglage : variable d'environnement d'abord (meme vide), puis .env."""
    if name in os.environ:
        return os.environ[name]
    env_path = ROOT / ".env"
    if env_path.exists():
        return read_env_file(env_path).get(name)
    return None


def admin_password() -> str | None:
    """Mot de passe du tableau de bord, ou rien s'il n'est pas configure.

    La valeur d'exemple de .env.example est refusee : un modele public ne doit pas
    devenir un vrai mot de passe par oubli.
    """
    value = setting("ADMIN_PASSWORD")
    if not value or value == ADMIN_EXAMPLE_VALUE:
        return None
    return value


def sqlalchemy_url() -> URL:
    """Adresse de la base au format SQLAlchemy, avec le pilote psycopg 3."""
    return make_url(database_url()).set(drivername="postgresql+psycopg")
