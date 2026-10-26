from alembic import command
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import URL

from tests.support import EXPECTED_TABLES, alembic_config, upgrade_head


def table_names(url: URL) -> set[str]:
    engine = create_engine(url)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_upgrade_creates_all_tables(empty_db_url: URL) -> None:
    upgrade_head(empty_db_url)
    assert table_names(empty_db_url) == EXPECTED_TABLES | {"alembic_version"}


def test_downgrade_removes_everything_and_upgrade_works_again(empty_db_url: URL) -> None:
    upgrade_head(empty_db_url)
    command.downgrade(alembic_config(empty_db_url), "base")
    assert table_names(empty_db_url) == {"alembic_version"}
    upgrade_head(empty_db_url)
    assert table_names(empty_db_url) == EXPECTED_TABLES | {"alembic_version"}
