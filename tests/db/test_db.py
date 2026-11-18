from unittest.mock import patch

from sqlalchemy.exc import OperationalError

from app.db.db import Database


def test_health_error_names_the_failed_database_check(database: Database) -> None:
    assert database.health_error() is None

    with patch("app.db.db.Session.execute", side_effect=OperationalError("SELECT 1", {}, Exception("down"))):
        assert database.health_error() == "Database check failed: OperationalError"
