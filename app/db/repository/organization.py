from typing import Sequence
from uuid import UUID

from sqlalchemy import ColumnElement, and_, select, update
from sqlalchemy.exc import SQLAlchemyError

from app.db.decorator import repository
from app.db.models.organization import OrganizationEntity
from app.db.repository.base import RepositoryBase, scopes_contains_conditions


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

    def get_one(self, id: UUID) -> OrganizationEntity | None:
        stmt = select(OrganizationEntity).where(self._and_clause(id))
        return self.db_session.execute(stmt).scalar()

    def exists(self, id: UUID) -> bool:
        stmt = select(select(OrganizationEntity.id).where(self._and_clause(id)).exists())
        return bool(self.db_session.execute(stmt).scalar())

    def get_one_by_register_id(self, register_id: str) -> OrganizationEntity | None:
        stmt = select(OrganizationEntity).where(
            and_(
                OrganizationEntity.register_id == register_id,
                OrganizationEntity.deleted_at.is_(None),
            )
        )
        return self.db_session.execute(stmt).scalar()

    def get_many(
        self,
        register_id: str | None = None,
        name: str | None = None,
        scopes: str | None = None,
        include_deleted: bool = False,
    ) -> Sequence[OrganizationEntity]:
        conditions: list[ColumnElement[bool]] = []
        if not include_deleted:
            conditions.append(OrganizationEntity.deleted_at.is_(None))
        if register_id:
            conditions.append(OrganizationEntity.register_id == register_id)
        if name:
            conditions.append(OrganizationEntity.name == name)
        conditions.extend(scopes_contains_conditions(OrganizationEntity.scopes, scopes))
        stmt = select(OrganizationEntity)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        return self.db_session.execute(stmt).scalars().all()

    def update(self, id: UUID, **kwargs: object) -> OrganizationEntity | None:
        try:
            target = {k: kwargs[k] for k in OrganizationEntity.__table__.columns.keys() if k in kwargs}
            if not target:
                return None
            stmt = update(OrganizationEntity).where(self._and_clause(id)).values(target).returning(OrganizationEntity)
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
