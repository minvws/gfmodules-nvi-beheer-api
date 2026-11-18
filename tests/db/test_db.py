from unittest.mock import patch

from sqlalchemy.exc import OperationalError

from app.db.db import Database

CONNECTION_REFUSED = OperationalError(
    "SELECT 1", {}, Exception("connection failed: Connection refused\n\tIs the server running on that host?")
)


def test_health_error_reports_the_database_failure(database: Database) -> None:
    assert database.health_error() is None

    with patch("app.db.db.Session.execute", side_effect=CONNECTION_REFUSED):
        assert database.health_error() == "Database check failed: connection failed: Connection refused"

    with patch("app.db.db.Session.execute", side_effect=TimeoutError()):
        assert database.health_error() == "Database check failed: TimeoutError"
