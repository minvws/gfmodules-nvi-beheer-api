from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from gfmodules.logging.testing import capture_records

from app.container import get_database
from app.db.db import Database
from app.logging.events import Log
from app.routers.health import router

DATABASE_DOWN = "Database check failed: connection refused"


def test_health_reports_the_database() -> None:
    db = MagicMock(spec=Database)
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_database] = lambda: db
    client = TestClient(app)

    with capture_records("app.routers.health") as captured:
        db.health_error.return_value = None
        healthy = client.get("/health")
        db.health_error.return_value = DATABASE_DOWN
        unhealthy = client.get("/health")

    assert healthy.status_code == 200
    assert healthy.json() == {"status": "ok", "components": {"database": "ok"}}
    assert unhealthy.status_code == 503
    assert unhealthy.json() == {"status": "error", "components": {"database": "error"}}
    events = captured.for_event(Log.HEALTH_UNHEALTHY)
    assert len(events) == 1
    assert events[0].message["component"] == "database"
    assert events[0].message["status"] == "error"
    assert events[0].message["error_detail"] == DATABASE_DOWN
