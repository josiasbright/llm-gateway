import app
from app.config import ROOT, read_env_file


def test_version_is_defined() -> None:
    assert app.__version__ == "0.1.0"


def test_env_example_lists_required_variables() -> None:
    values = read_env_file(ROOT / ".env.example")
    for name in (
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
        "POSTGRES_PORT",
        "DATABASE_URL",
        "ADMIN_PASSWORD",
    ):
        assert values.get(name), f"{name} doit être défini et non vide dans .env.example"


def test_env_file_is_ignored_by_git() -> None:
    lines = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".env" in lines
