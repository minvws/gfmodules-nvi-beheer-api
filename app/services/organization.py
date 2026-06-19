from datetime import datetime
from typing import Any, List
from uuid import UUID

from app import scope_utils
from app.db.db import Database
from app.db.models.organization import OrganizationEntity
from app.db.repository.organization import OrganizationRepository
from app.models.ura import UraNumber
from app.services.exceptions import ScopeNotAllowedError, ScopesNotGrantedError


class OrganizationService:
    def __init__(self, db: Database, allowed_scopes: List[str]) -> None:
        self.db = db
        self.allowed_scopes = allowed_scopes

    def create_one(
        self,
        register_id: UraNumber,
        name: str,
        scopes: str | None = None,
    ) -> OrganizationEntity:
        if scopes:
            scope_allowed = scope_utils.check_allowed(self.allowed_scopes, scopes)
            if not scope_allowed:
                raise ScopeNotAllowedError(scopes)

        with self.db.get_db_session() as session:
            repo = session.get_repository(OrganizationRepository)
            entity = OrganizationEntity(register_id=register_id, name=name, scopes=scopes)
            return repo.add_one(entity)

    def get_one(self, id: UUID) -> OrganizationEntity | None:
        with self.db.get_db_session() as session:
            repo = session.get_repository(OrganizationRepository)
            return repo.get_one(id)

    def exists(self, id: UUID) -> bool:
        with self.db.get_db_session() as session:
            repo = session.get_repository(OrganizationRepository)
            return repo.exists(id)

    def get_many(
        self,
        register_id: UraNumber | None = None,
        name: str | None = None,
        scopes: str | None = None,
        include_deleted: bool = False,
    ) -> List[OrganizationEntity]:
        with self.db.get_db_session() as session:
            repo = session.get_repository(OrganizationRepository)
            return list(
                repo.get_many(
                    register_id=register_id,
                    name=name,
                    scopes=scopes,
                    include_deleted=include_deleted,
                )
            )

    def update_one(self, id: UUID, **kwargs: Any) -> OrganizationEntity | None:
        if "scopes" in kwargs:
            scopes: str = kwargs["scopes"]
            valid_scope = scope_utils.check_allowed(self.allowed_scopes, scopes)
            if not valid_scope:
                raise ScopeNotAllowedError(scopes)

        with self.db.get_db_session() as session:
            repo = session.get_repository(OrganizationRepository)
            return repo.update(id, **kwargs)

    def delete_one(self, id: UUID) -> OrganizationEntity | None:
        with self.db.get_db_session() as session:
            repo = session.get_repository(OrganizationRepository)
            return repo.update(id, deleted_at=datetime.now())

    def assert_scopes_granted(self, organization_id: UUID, requested: str | None) -> None:
        organization = self.get_one(organization_id)
        available = organization.scopes if organization is not None else None
        if not scope_utils.is_subset(requested, available):
            ungranted = scope_utils.parse(requested) - scope_utils.parse(available)
            raise ScopesNotGrantedError(ungranted)
