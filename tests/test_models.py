from sqlalchemy import Connection, inspect

from app.db.models import Base
from tests.support import EXPECTED_TABLES


def test_models_cover_exactly_the_migrated_tables() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_model_columns_match_database_columns(conn: Connection) -> None:
    inspector = inspect(conn)
    for table_name, table in Base.metadata.tables.items():
        database_columns = {column["name"] for column in inspector.get_columns(table_name)}
        assert {column.name for column in table.columns} == database_columns, table_name
