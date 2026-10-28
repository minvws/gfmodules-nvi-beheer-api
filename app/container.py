import logging

import inject

from app.config import Config, get_config
from app.db.db import Database
from app.services.certificate import ClientCertificateService, OrganizationCertificateService
from app.services.client import ClientService
from app.services.organization import OrganizationService
from app.services.scopes.client_scopes import ClientScopesService
from app.services.scopes.org_scopes import OrganizationScopesService
from app.services.source.client_source import ClientSourceService
from app.services.source.organization_source import OrganizationSourceService

logger = logging.getLogger(__name__)


def container_config(binder: inject.Binder) -> None:
    config = get_config()
    binder.bind(Config, config)

    db = Database(config_database=config.database)
    binder.bind(Database, db)

    organization_service = OrganizationService(db)
    binder.bind(OrganizationService, organization_service)

    client_service = ClientService(db)
    binder.bind(ClientService, client_service)

    org_scopes_service = OrganizationScopesService(db)
    binder.bind(OrganizationScopesService, org_scopes_service)

    client_scopes_service = ClientScopesService(db)
    binder.bind(ClientScopesService, client_scopes_service)

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


def get_org_scopes_service() -> OrganizationScopesService:
    return inject.instance(OrganizationScopesService)


def get_client_scopes_service() -> ClientScopesService:
    return inject.instance(ClientScopesService)


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
