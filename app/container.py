import logging

import inject

from app.config import Config, get_config
from app.db.db import Database
from app.services.certificate import ClientCertificateService, OrganizationCertificateService
from app.services.client import ClientService
from app.services.organization import OrganizationService
from app.services.scopes import ScopeService
from app.services.source.client_source import ClientSourceService
from app.services.source.organization_source import OrganizationSourceService

logger = logging.getLogger(__name__)


def container_config(binder: inject.Binder) -> None:
    config = get_config()
    binder.bind(Config, config)

    db = Database(config_database=config.database)
    binder.bind(Database, db)

    scope_service = ScopeService()
    binder.bind(ScopeService, scope_service)

    organization_service = OrganizationService(db)
    binder.bind(OrganizationService, organization_service)

    client_service = ClientService(db)
    binder.bind(ClientService, client_service)

    org_certificate_service = OrganizationCertificateService(db)
    binder.bind(OrganizationCertificateService, org_certificate_service)

    client_certificate_service = ClientCertificateService(db)
    binder.bind(ClientCertificateService, client_certificate_service)

    org_source_service = OrganizationSourceService(db)
    binder.bind(OrganizationSourceService, org_source_service)

    client_source_service = ClientSourceService(db)
    binder.bind(ClientSourceService, client_source_service)


def get_database() -> Database:
    return inject.instance(Database)


def get_allowed_scopes() -> set[str]:
    return inject.instance("allowed_scopes")  # type: ignore


def get_organization_service() -> OrganizationService:
    return inject.instance(OrganizationService)


def get_client_service() -> ClientService:
    return inject.instance(ClientService)


def get_scope_service() -> ScopeService:
    return inject.instance(ScopeService)


def get_org_certificate_service() -> OrganizationCertificateService:
    return inject.instance(OrganizationCertificateService)


def get_client_certificate_service() -> ClientCertificateService:
    return inject.instance(ClientCertificateService)


def get_organization_source_service() -> OrganizationSourceService:
    return inject.instance(OrganizationSourceService)


def get_client_source_service() -> ClientSourceService:
    return inject.instance(ClientSourceService)


def configure() -> None:
    inject.configure(container_config, once=True)
