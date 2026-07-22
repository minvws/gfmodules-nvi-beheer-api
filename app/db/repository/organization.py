from typing import Sequence
from uuid import UUID

from sqlalchemy import ColumnElement, and_, or_, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import contains_eager, joinedload, selectinload

from app.db.decorator import repository
from app.db.models.client import ClientEntity

# from app.db.models.client_scope import ClientScopeEntity
from app.db.models.organization import OrganizationEntity
from app.db.models.scope import ScopeEntity
from app.db.repository.base import RepositoryBase
from app.models.ura import UraNumber


@repository(OrganizationEntity)
class OrganizationRepository(RepositoryBase):
    def add_one(self, data: OrganizationEntity) -> OrganizationEntity:
        try:
            self.db_session.add(data)
            self.db_session.commit()
            return data
        except SQLAlchemyError as e:
            self.db_session.rollback()
            raise e

    def find_one(
        self, id: UUID, with_clients: bool = False
    ) -> OrganizationEntity | None:
        stmt = select(OrganizationEntity).options(
            selectinload(OrganizationEntity.scopes)
        )
        if not with_clients:
            stmt = stmt.where(self._and_clause(id))
        else:
            stmt = stmt.where(OrganizationEntity.id == id).options(
                joinedload(OrganizationEntity.clients)
            )

        return self.db_session.execute(stmt).unique().scalar()

    def exists(self, id: UUID) -> bool:
        stmt = select(
            select(OrganizationEntity.id).where(self._and_clause(id)).exists()
        )
        return bool(self.db_session.execute(stmt).scalar())

    def find_one_by_register_id(
        self, register_id: UraNumber
    ) -> OrganizationEntity | None:
        stmt = select(OrganizationEntity).where(
            and_(
                OrganizationEntity.register_id == register_id,
                OrganizationEntity.deleted_at.is_(None),
            )
        )
        return self.db_session.execute(stmt).scalar()

    def find_one_with_specific_client(
        self, id: UUID, client_id: UUID
    ) -> OrganizationEntity | None:
        stmt = (
            select(OrganizationEntity)
            .join(OrganizationEntity.clients)
            .join(ClientEntity.scopes)
            # .join(ClientScopeEntity.scope)
            .where(OrganizationEntity.id == id, ClientEntity.id == client_id)
            .options(
                selectinload(OrganizationEntity.scopes),
                contains_eager(OrganizationEntity.clients).contains_eager(
                    ClientEntity.scopes
                ),
                # .contains_eager(ClientScopeEntity.scope),
            )
        )
        return self.db_session.execute(stmt).unique().scalar_one_or_none()

    def find_many(
        self,
        register_id: UraNumber | None = None,
        name: str | None = None,
        scopes: list[str] | None = None,
        include_deleted: bool = False,
    ) -> Sequence[OrganizationEntity]:
        conditions: list[ColumnElement[bool]] = []
        if not include_deleted:
            conditions.append(OrganizationEntity.deleted_at.is_(None))
        if register_id:
            conditions.append(OrganizationEntity.register_id == register_id)
        if name:
            conditions.append(OrganizationEntity.name == name)

        if scopes:
            scopes_conditions = [(ScopeEntity.name == s) for s in scopes]
            conditions.append(or_(*scopes_conditions))

        stmt = (
            select(OrganizationEntity)
            .join(ScopeEntity)
            .options(selectinload(OrganizationEntity.scopes))
        )
        if conditions:
            stmt = stmt.where(and_(*conditions))

        return self.db_session.execute(stmt).scalars().unique().all()

    def update(self, id: UUID, **kwargs: object) -> OrganizationEntity | None:
        try:
            target = {
                k: kwargs[k]
                for k in OrganizationEntity.__table__.columns.keys()
                if k in kwargs
            }
            if not target:
                return None
            stmt = (
                update(OrganizationEntity)
                .where(self._and_clause(id))
                .values(target)
                .returning(OrganizationEntity)
            )
            result = self.db_session.execute(stmt).scalar_one_or_none()
            self.db_session.commit()
            return result
        except SQLAlchemyError as e:
            self.db_session.rollback()
            raise e

    def _and_clause(self, id: UUID) -> ColumnElement[bool]:
        return and_(
            OrganizationEntity.id == id,
            OrganizationEntity.deleted_at.is_(None),
        )
