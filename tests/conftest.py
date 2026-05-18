from typing import Any, Generator

import inject
import pytest
from fastapi.testclient import TestClient

from app.application import setup_fastapi
from app.config import ConfigDatabase, set_config
from app.db.db import Database
from app.db.models.healthcare_provider import HealthcareProviderEntity
from app.db.repository.healthcare_provider import HealthcareProvidersRepository
from app.models.oin_number import OinNumber
from app.models.ura_number import UraNumber
from app.services.healthcare_provider import HeatlhcareProviderService
from tests.test_config import get_test_config


@pytest.fixture()
def database() -> Generator[Database, Any, None]:
    config_database = ConfigDatabase(dsn="sqlite:///:memory:", retry_backoff=[])
    db = Database(config_database=config_database)
    db.generate_tables()
    yield db
    db.close()


@pytest.fixture()
def load_config() -> None:
    test_config = get_test_config()
    set_config(test_config)


@pytest.fixture()
def client(load_config: None, database: Database) -> Generator[TestClient, Any, None]:
    inject.clear()

    def test_container_config(binder: inject.Binder) -> None:
        binder.bind(Database, database)
        binder.bind(HeatlhcareProviderService, HeatlhcareProviderService(database))

    inject.configure(test_container_config, once=False)

    app = setup_fastapi()
    client = TestClient(app)

    yield client

    inject.clear()


@pytest.fixture()
def healthcare_provider_repository(database: Database) -> HealthcareProvidersRepository:
    return HealthcareProvidersRepository(db_session=database.get_db_session())


@pytest.fixture()
def healthcare_provider_service(database: Database) -> HeatlhcareProviderService:
    return HeatlhcareProviderService(database)


@pytest.fixture()
def ura_number() -> UraNumber:
    return UraNumber("00000123")


@pytest.fixture()
def oin() -> OinNumber:
    return OinNumber("00000003123456780001")


@pytest.fixture()
def healthcare_provider_entity(ura_number: UraNumber, oin: OinNumber) -> HealthcareProviderEntity:
    return HealthcareProviderEntity(
        ura_number=ura_number.value,
        source_id="some_source_id",
        is_source=True,
        is_viewer=True,
        oin=oin.value,
        common_name="some_common_name",
        status="active",
    )
