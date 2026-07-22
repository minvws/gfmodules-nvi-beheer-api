from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import HTTPException

from app import scope_utils
from app.db.db import Database
from app.db.models.organization import OrganizationEntity
from app.db.models.scope import ScopeEntity
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
            entity = OrganizationEntity(register_id=register_id, name=name, scopes=[])
            if scopes:
                scopes_repo = session.get_repository(ScopeRepository)
                app_scopes = scopes_repo.find_many()
                # TODO: validate against scopes in db
                valid_scopes = ScopeService.validate_requested_scopes(app_scopes, scopes)
                if not valid_scopes:
                    raise ScopeNotAllowedError(scopes)

                org_scopes = ScopeService.make_scope_subset(app_scopes, scopes)
                entity.scopes = org_scopes

            return org_repo.add_one(entity)

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

    def update_one(self, id: UUID, name: str, scope: List[str] | None = None) -> OrganizationEntity | None:
        if scope:
            valid_scope = self.scope_service.check_incoming_scope(scope)
            if not valid_scope:
                raise ScopeNotAllowedError(scope)

        with self.db.get_db_session() as session:
            repo = session.get_repository(OrganizationRepository)
            org = repo.find_one(id)
            if not org:
                raise HTTPException(status_code=404)
            org.name = name

            if scope is None:
                org.scopes = []
                session.add(org)
                session.commit()
                return org

            org_scope_map = {s.name: s for s in org.scopes} if org.scopes else {}
            reconciled_scopes = []
            for s in scope:
                if s in org_scope_map:
                    existing_scope = org_scope_map[s]
                    reconciled_scopes.append(existing_scope)

                else:
                    new_scope = ScopeEntity(name=s)
                    reconciled_scopes.append(new_scope)

            if org.scopes:
                org.scopes.clear()
                org.scopes.extend(reconciled_scopes)
            else:
                org.scopes = reconciled_scopes
            session.add(org)
            session.commit()

            return org

    def delete_one(self, id: UUID) -> OrganizationEntity | None:
        with self.db.get_db_session() as session:
            repo = session.get_repository(OrganizationRepository)
            org = repo.find_one(id, with_clients=True)
            if org is None:
                return None
            if org.clients and any(client.deleted_at is None for client in org.clients):
                raise OrganizationHasActiveClientsError(id)
            return repo.update(id, deleted_at=datetime.now())

    # TODO: This does not belong here
    @staticmethod
    def assert_scopes_granted(organization: OrganizationEntity, requested: List[str]) -> None:
        available = organization.org_scopes if organization is not None else None
        if not scope_utils.is_subset(available, requested):
            ungranted = set(requested) - set(available or [])
            raise ScopesNotGrantedError(ungranted)
