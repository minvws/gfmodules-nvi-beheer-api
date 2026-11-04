from sqlalchemy import inspect

from app.db.db import Database
from app.db.models.base import Base


def test_all_tables_live_in_admin_schema() -> None:
    assert {table.fullname for table in Base.metadata.tables.values() if table.schema != "admin"} == set()


def test_tables_are_created_in_admin_schema(database: Database) -> None:
    assert set(inspect(database.engine).get_table_names(schema="admin")) == {
        table.name for table in Base.metadata.tables.values()
    }
