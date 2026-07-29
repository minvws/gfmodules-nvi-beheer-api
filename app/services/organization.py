from datetime import datetime
from uuid import UUID

from fastapi import HTTPException

from app import scope_utils
from app.db.db import Database
from app.db.models.organization import OrganizationEntity
from app.db.repository.organization import OrganizationRepository
from app.db.repository.scope import ScopeRepository
from app.models.ura import UraNumber
from app.services.exceptions import (
    OrganizationHasActiveClientsError,
    ScopeNotAllowedError,
    ScopesNotGrantedError,
)
from app.services.scopes import ScopeService


class OrganizationService:
    def __init__(self, db: Database, scopes_service: ScopeService) -> None:
        self.db = db
        self.scope_service = scopes_service

    def create_one(
        self,
        register_id: UraNumber,
        name: str,
        scopes: list[str] | None = None,
    ) -> OrganizationEntity:
        with self.db.get_db_session() as session:
            org_repo = session.get_repository(OrganizationRepository)
            entity = OrganizationEntity(
                register_id=register_id,
                name=name,
            )
            if scopes:
                scopes_repo = session.get_repository(ScopeRepository)
                app_scopes = scopes_repo.find_many()
                valid_scopes = ScopeService.validate_requested_scopes(app_scopes, scopes)
                if not valid_scopes:
                    raise ScopeNotAllowedError(scopes)

                org_scopes = [s for s in app_scopes if s.name in scopes]
                entity.scopes = org_scopes

            new_org = org_repo.add_one(entity)

            return new_org

    def get_one(self, id: UUID, with_clients: bool = False) -> OrganizationEntity | None:
        with self.db.get_db_session() as session:
            repo = session.get_repository(OrganizationRepository)
            entity = repo.find_one(id, with_clients=with_clients)
            return entity

    def exists(self, id: UUID) -> bool:
        with self.db.get_db_session() as session:
            repo = session.get_repository(OrganizationRepository)
            return repo.exists(id)

    def get_many(
        self,
        register_id: UraNumber | None = None,
        name: str | None = None,
        scopes: list[str] | None = None,
        include_deleted: bool = False,
    ) -> list[OrganizationEntity]:
        with self.db.get_db_session() as session:
            repo = session.get_repository(OrganizationRepository)
            orgs = repo.find_many(
                register_id=register_id,
                name=name,
                scopes=scopes,
                include_deleted=include_deleted,
            )
            return list(orgs)

    def update_one(self, id: UUID, name: str, scope: list[str] | None = None) -> OrganizationEntity | None:
        with self.db.get_db_session() as session:
            org_repo = session.get_repository(OrganizationRepository)
            scope_repo = session.get_repository(ScopeRepository)
            app_scope = scope_repo.find_many()

            org = org_repo.find_one(id)
            if not org:
                raise HTTPException(status_code=404)
            org.name = name

            if not scope:
                org.scopes = []
                session.add(org)
                session.commit()
                return org

            valid_scopes = ScopeService.validate_requested_scopes(app_scope, scope)
            if not valid_scopes:
                raise ScopeNotAllowedError(scope)

            org_scopes = [s for s in app_scope if s.name in scope]
            org.scopes = org_scopes
            updated_org = org_repo.add_one(org)

            return updated_org

    def delete_one(self, id: UUID) -> OrganizationEntity | None:
        with self.db.get_db_session() as session:
            repo = session.get_repository(OrganizationRepository)
            org = repo.find_one(id, with_clients=True)
            if org is None:
                return None
            if org.clients and any(client.deleted_at is None for client in org.clients):
                raise OrganizationHasActiveClientsError(id)

            org.deleted_at = datetime.now()
            org.scopes.clear()

            session.add(org)
            session.commit()
            session.session.refresh(org)

            return org

    # TODO: This does not belong here

    @staticmethod
    def assert_scopes_granted(organization: OrganizationEntity, requested: list[str]) -> None:
        available = organization.org_scopes if organization is not None else None
        if not scope_utils.is_subset(available, requested):
            ungranted = set(requested) - set(available or [])
            raise ScopesNotGrantedError(ungranted)
