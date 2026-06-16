from datetime import datetime
from typing import Any, Generator
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import ConfigDatabase
from app.container import get_client_service, get_organization_service
from app.db.db import Database
from app.db.models.client import ClientEntity
from app.db.models.organization import OrganizationEntity
from app.db.repository.client import ClientRepository
from app.db.repository.organization import OrganizationRepository
from app.routers.client import router as client_router
from app.routers.organization import router as organization_router
from app.routers.resolve import router as resolve_router
from app.services.client import ClientService
from app.services.organization import OrganizationService

TEST_OIN = "00000099000000001000"
TEST_REGISTER_ID = "test-register-001"
TEST_ORG_NAME = "Test Organization"
TEST_MANDATE_ID = "mandate-001"
TEST_COMMON_NAME = "Test Client"
VALID_OIN = TEST_OIN
FIXED_CREATED_AT = datetime(2024, 1, 1, 12, 0, 0)


@pytest.fixture()
def database() -> Generator[Database, Any, None]:
    config_database = ConfigDatabase(dsn="sqlite:///:memory:", retry_backoff=[])
    db = Database(config_database=config_database)
    db.generate_tables()
    yield db
    db.engine.dispose()


@pytest.fixture()
def organization_repository(database: Database) -> OrganizationRepository:
    return OrganizationRepository(db_session=database.get_db_session())


@pytest.fixture()
def client_repository(database: Database) -> ClientRepository:
    return ClientRepository(db_session=database.get_db_session())


@pytest.fixture()
def organization_service(database: Database) -> OrganizationService:
    return OrganizationService(database)


@pytest.fixture()
def client_service(database: Database, organization_service: OrganizationService) -> ClientService:
    return ClientService(database, organization_service)


@pytest.fixture()
def organization_entity() -> OrganizationEntity:
    return OrganizationEntity(register_id=TEST_REGISTER_ID, name=TEST_ORG_NAME)


@pytest.fixture()
def persisted_organization(organization_service: OrganizationService) -> OrganizationEntity:
    return organization_service.create_one(register_id=TEST_REGISTER_ID, name=TEST_ORG_NAME)


@pytest.fixture()
def client_entity(persisted_organization: OrganizationEntity) -> ClientEntity:
    return ClientEntity(
        organization_id=persisted_organization.id,
        mandate_id=TEST_MANDATE_ID,
        oin=TEST_OIN,
        common_name=TEST_COMMON_NAME,
    )


@pytest.fixture()
def mock_client_service() -> MagicMock:
    return MagicMock(spec=ClientService)


@pytest.fixture()
def mock_organization_service() -> MagicMock:
    service = MagicMock(spec=OrganizationService)
    service.exists.return_value = True
    return service


@pytest.fixture()
def api(mock_client_service: MagicMock, mock_organization_service: MagicMock) -> TestClient:
    app = FastAPI()
    for router in (organization_router, client_router, resolve_router):
        app.include_router(router)
    app.dependency_overrides[get_client_service] = lambda: mock_client_service
    app.dependency_overrides[get_organization_service] = lambda: mock_organization_service
    return TestClient(app)


def make_organization_entity(
    *,
    id: UUID | None = None,
    register_id: str = VALID_OIN,
    name: str = "Test Organization",
    scopes: str | None = None,
    deleted_at: datetime | None = None,
) -> OrganizationEntity:
    return OrganizationEntity(
        id=id or uuid4(),
        register_id=register_id,
        name=name,
        scopes=scopes,
        created_at=FIXED_CREATED_AT,
        deleted_at=deleted_at,
    )


def make_client_entity(
    *,
    id: UUID | None = None,
    organization_id: UUID | None = None,
    oin: str = VALID_OIN,
    common_name: str = "Test Client",
    mandate_id: str = "mandate-1",
    scopes: str | None = None,
    deleted_at: datetime | None = None,
) -> ClientEntity:
    return ClientEntity(
        id=id or uuid4(),
        organization_id=organization_id or uuid4(),
        oin=oin,
        common_name=common_name,
        mandate_id=mandate_id,
        scopes=scopes,
        created_at=FIXED_CREATED_AT,
        deleted_at=deleted_at,
    )
