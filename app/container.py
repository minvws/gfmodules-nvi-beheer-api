import logging

import inject

from app.config import Config, get_config
from app.db.db import Database
from app.services.client import ClientService
from app.services.organization import OrganizationService
from app.services.scopes import ScopeService

logger = logging.getLogger(__name__)


def container_config(binder: inject.Binder) -> None:
    config = get_config()
    binder.bind(Config, config)

    allowed_scopes = config.app.scopes
    binder.bind("allowed_scopes", allowed_scopes)

    db = Database(config_database=config.database)
    binder.bind(Database, db)

    scope_service = ScopeService(db)
    binder.bind(ScopeService, scope_service)

    organization_service = OrganizationService(db, scope_service)
    binder.bind(OrganizationService, organization_service)

    client_service = ClientService(db, organization_service)
    binder.bind(ClientService, client_service)


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


def configure() -> None:
    inject.configure(container_config, once=True)
