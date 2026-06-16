import logging

import inject

from app.config import Config, get_config
from app.db.db import Database
from app.services.client import ClientService
from app.services.organization import OrganizationService

logger = logging.getLogger(__name__)


def container_config(binder: inject.Binder) -> None:
    config = get_config()
    binder.bind(Config, config)

    db = Database(config_database=config.database)
    binder.bind(Database, db)

    organization_service = OrganizationService(db)
    binder.bind(OrganizationService, organization_service)

    client_service = ClientService(db, organization_service)
    binder.bind(ClientService, client_service)


def get_database() -> Database:
    return inject.instance(Database)


def get_organization_service() -> OrganizationService:
    return inject.instance(OrganizationService)


def get_client_service() -> ClientService:
    return inject.instance(ClientService)


def configure() -> None:
    inject.configure(container_config, once=True)
