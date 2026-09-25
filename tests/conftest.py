from collections.abc import Generator
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import gfmodules.logging as gflog
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from gfmodules.logging import ConfigLogging
from gfmodules.logging.testing import reset_for_tests
from pydantic import SecretStr
from sqlalchemy import text

from app.config import ConfigDatabase
from app.container import get_client_service, get_organization_service
from app.db.db import Database
from app.db.models.certificate import CertificateEntity
from app.db.models.client import ClientEntity
from app.db.models.organization import OrganizationEntity
from app.db.models.source import SourceEntity
from app.db.repository.certificate import CertificateRepository
from app.db.repository.client import ClientRepository
from app.db.repository.organization import OrganizationRepository
from app.db.repository.source import SourceRepository
from app.logging.events import Log
from app.models.certificates import CertificateCreate
from app.models.client import ClientCreate
from app.models.oin import Oin
from app.models.organization import OrganizationCreate
from app.models.source import SourceCreate
from app.models.ura import UraNumber
from app.routers.client import router as client_router
from app.routers.organization import router as organization_router
from app.routers.resolve import router as resolve_router
from app.services.certificate.client_certificate import ClientCertificateService
from app.services.certificate.organization_certificate import OrganizationCertificateService
from app.services.client import ClientService
from app.services.organization import OrganizationService
from app.services.source.client_source import ClientSourceService
from app.services.source.organization_source import OrganizationSourceService

TEST_OIN = Oin("00000099000000001000")
TEST_EXTERNAL_ID = UraNumber("12345678")
TEST_ORG_NAME = "Test Organization"
TEST_SCOPES = "nvi:create nvi:read nvi:delete nvi:localize"
TEST_CLIENT_NAME = "Test Client"
TEST_SOURCE_ID = "source-001"
TEST_SOURCE_NAME = "test-source-1"
TEST_DOMAIN = "example.com"
VALID_OIN = TEST_OIN
FIXED_CREATED_AT = datetime(2024, 1, 1, 12, 0, 0)

SECOND_EXTERNAL_ID = UraNumber("87654321")
SECOND_ORG_NAME = "Second Test Organization"
SECON_SCOPES = "nvi:create nvi:localize"
SECOND_OIN = Oin("00000099000000002000")
SECOND_DOMAIN = "Other-Domain"
SECOND_CLIENT_NAME = "Test Client 2"
SECOND_SOURCE_ID = "source-002"
SECOND_SOURCE_NAME = "test-source-2"


@pytest.fixture(autouse=True)
def logging_catalogue() -> Generator[None, Any, None]:
    gflog.configure(
        config=ConfigLogging(console_streams=["debug"], access_logs=True),
        loglevel="DEBUG",
        catalogue=Log,
        strict_fields=True,
    )
    try:
        yield
    finally:
        reset_for_tests()


@pytest.fixture()
def database() -> Generator[Database, Any, None]:
    config_database = ConfigDatabase(dsn=SecretStr("sqlite:///:memory:"), retry_backoff=[])
    db = Database(config_database=config_database)
    db.generate_tables()
    # setup system scopes
    stmt = text("INSERT INTO scopes (name) VALUES ('nvi:create'), ('nvi:delete'),('nvi:read'),('nvi:localize');")
    with db.get_db_session() as session:
        session.session.execute(stmt)
        session.commit()

    yield db
    db.engine.dispose()


@pytest.fixture()
def organization_repository(database: Database) -> OrganizationRepository:
    return OrganizationRepository(db_session=database.get_db_session())


@pytest.fixture()
def client_repository(database: Database) -> ClientRepository:
    return ClientRepository(db_session=database.get_db_session())


@pytest.fixture()
def certificate_repository(database: Database) -> CertificateRepository:
    return CertificateRepository(db_session=database.get_db_session())


@pytest.fixture()
def source_repository(database: Database) -> SourceRepository:
    return SourceRepository(db_session=database.get_db_session())


@pytest.fixture()
def organization_service(database: Database) -> OrganizationService:
    return OrganizationService(database)


@pytest.fixture()
def client_service(
    database: Database,
) -> ClientService:
    return ClientService(database)


@pytest.fixture()
def organization_certificate_service(database: Database) -> OrganizationCertificateService:
    return OrganizationCertificateService(database)


@pytest.fixture()
def client_certificate_service(database: Database) -> ClientCertificateService:
    return ClientCertificateService(database)


@pytest.fixture()
def organization_source_service(database: Database) -> OrganizationSourceService:
    return OrganizationSourceService(database)


@pytest.fixture()
def client_source_service(database: Database) -> ClientSourceService:
    return ClientSourceService(database)


@pytest.fixture()
def organization_entity() -> OrganizationEntity:
    return OrganizationEntity(external_id=TEST_EXTERNAL_ID, name=TEST_ORG_NAME)


@pytest.fixture()
def client_entity() -> ClientEntity:
    return ClientEntity(name=TEST_CLIENT_NAME, description="Test description")


@pytest.fixture()
def certificate_entity() -> CertificateEntity:
    return CertificateEntity(organization_identifier=TEST_OIN, domain="example.com")


@pytest.fixture()
def source_entity() -> SourceEntity:
    return SourceEntity(source_id=TEST_SOURCE_ID, name="Source Example")


@pytest.fixture()
def cert_create_dto_1() -> CertificateCreate:
    return CertificateCreate(organization_identifier=TEST_OIN, domain=TEST_DOMAIN)


@pytest.fixture()
def cert_create_dto_2() -> CertificateCreate:
    return CertificateCreate(organization_identifier=SECOND_OIN, domain=SECOND_DOMAIN)


@pytest.fixture()
def source_create_dto_1() -> SourceCreate:
    return SourceCreate(source_id=TEST_SOURCE_ID, name=TEST_SOURCE_NAME)


@pytest.fixture()
def source_create_dto_2() -> SourceCreate:
    return SourceCreate(source_id=SECOND_SOURCE_ID, name=SECOND_SOURCE_NAME)


@pytest.fixture()
def client_create_dto_1(
    cert_create_dto_1: CertificateCreate, source_create_dto_1: SourceCreate, source_create_dto_2: SourceCreate
) -> ClientCreate:
    return ClientCreate(
        name=TEST_CLIENT_NAME,
        scopes="nvi:create nvi:read",
        certificates=[cert_create_dto_1],
        sources=[source_create_dto_1, source_create_dto_2],
    )


@pytest.fixture()
def org_create_dto_1(
    cert_create_dto_1: CertificateCreate,
    cert_create_dto_2: CertificateCreate,
    source_create_dto_1: SourceCreate,
    client_create_dto_1: ClientCreate,
    source_create_dto_2: SourceCreate,
) -> OrganizationCreate:
    return OrganizationCreate(
        external_id=TEST_EXTERNAL_ID,
        name=TEST_ORG_NAME,
        scopes=TEST_SCOPES,
        certificates=[cert_create_dto_1, cert_create_dto_2],
        sources=[source_create_dto_1, source_create_dto_2],
        clients=[client_create_dto_1],
    )


@pytest.fixture()
def org_create_dto_2() -> OrganizationCreate:
    return OrganizationCreate(
        external_id=SECOND_EXTERNAL_ID,
        name=SECOND_ORG_NAME,
        scopes=SECON_SCOPES,
        sources=[SourceCreate(source_id="source-3", name="third-source")],
        certificates=[CertificateCreate(organization_identifier=SECOND_OIN, domain=SECOND_DOMAIN)],
        clients=[
            ClientCreate(
                name=SECOND_CLIENT_NAME,
                scopes="nvi:localize",
                sources=[SourceCreate(source_id="source-3", name="third-source")],
            )
        ],
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
def api(
    mock_client_service: MagicMock, organization_service: OrganizationService, client_service: ClientService
) -> TestClient:
    app = FastAPI()
    for router in (organization_router, client_router, resolve_router):
        app.include_router(router)
    app.dependency_overrides[get_client_service] = lambda: client_service
    app.dependency_overrides[get_organization_service] = lambda: organization_service
    return TestClient(app)


def make_organization_entity(
    *,
    id: UUID | None = None,
    external_id: UraNumber = TEST_EXTERNAL_ID,
    name: str = "Test Organization",
    scopes: str | None = None,
    deleted_at: datetime | None = None,
) -> OrganizationEntity:
    return OrganizationEntity(
        id=id or uuid4(),
        external_id=external_id,
        name=name,
        scopes=scopes,
        created_at=FIXED_CREATED_AT,
        deleted_at=deleted_at,
    )


def make_client_entity(
    *,
    id: UUID | None = None,
    organization_id: UUID | None = None,
    oin: Oin = VALID_OIN,
    common_name: str = "Test Client",
    source_id: str | None = None,
    scopes: str | None = None,
    deleted_at: datetime | None = None,
    org_entity: OrganizationEntity | None = None,
) -> ClientEntity:
    return ClientEntity(
        id=id or uuid4(),
        organization_id=organization_id or (org_entity.id if org_entity else uuid4()),
        oin=oin,
        common_name=common_name,
        source_id=source_id,
        scopes=scopes,
        created_at=FIXED_CREATED_AT,
        deleted_at=deleted_at,
        organization=org_entity,
    )
