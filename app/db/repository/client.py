from typing import Sequence
from uuid import UUID

from sqlalchemy import ColumnElement, and_, select, update
from sqlalchemy.exc import SQLAlchemyError

from app.db.decorator import repository
from app.db.models.client import ClientEntity
from app.db.models.organization import OrganizationEntity
from app.db.repository.base import RepositoryBase, scopes_contains_conditions
from app.models.oin import Oin
from app.models.ura import UraNumber


@repository(ClientEntity)
class ClientRepository(RepositoryBase):
    def add_one(self, data: ClientEntity) -> ClientEntity:
        try:
            self.db_session.add(data)
            self.db_session.commit()
            return data
        except SQLAlchemyError as e:
            self.db_session.rollback()
            raise e

    def get_one(self, organization_id: UUID, id: UUID) -> ClientEntity | None:
        stmt = select(ClientEntity).where(self._and_clause(organization_id, id))
        return self.db_session.execute(stmt).scalar_one_or_none()

    def exists(self, organization_id: UUID, id: UUID) -> bool:
        stmt = select(select(ClientEntity.id).where(self._and_clause(organization_id, id)).exists())
        return bool(self.db_session.execute(stmt).scalar())

    def get_by_credentials(self, common_name: str, oin: Oin, org_ura: UraNumber) -> ClientEntity | None:
        stmt = (
            select(ClientEntity)
            .join(OrganizationEntity, ClientEntity.organization_id == OrganizationEntity.id)
            .where(
                and_(
                    ClientEntity.common_name == common_name,
                    ClientEntity.oin == oin,
                    OrganizationEntity.register_id == org_ura,
                    OrganizationEntity.deleted_at.is_(None),
                    ClientEntity.deleted_at.is_(None),
                )
            )
        )
        return self.db_session.execute(stmt).scalar()

    def get_many(
        self,
        organization_id: UUID,
        oin: Oin | None = None,
        common_name: str | None = None,
        source_id: str | None = None,
        scopes: str | None = None,
        include_deleted: bool = False,
    ) -> Sequence[ClientEntity]:
        conditions: list[ColumnElement[bool]] = [ClientEntity.organization_id == organization_id]
        if not include_deleted:
            conditions.append(ClientEntity.deleted_at.is_(None))
        if oin:
            conditions.append(ClientEntity.oin == oin)
        if common_name:
            conditions.append(ClientEntity.common_name == common_name)
        if source_id:
            conditions.append(ClientEntity.source_id == source_id)
        conditions.extend(scopes_contains_conditions(ClientEntity.scopes, scopes))
        stmt = select(ClientEntity).where(and_(*conditions))
        return self.db_session.execute(stmt).scalars().all()

    def update(self, organization_id: UUID, id: UUID, **kwargs: object) -> ClientEntity | None:
        try:
            target = {k: kwargs[k] for k in ClientEntity.__table__.columns.keys() if k in kwargs}
            if not target:
                return None
            stmt = (
                update(ClientEntity).where(self._and_clause(organization_id, id)).values(target).returning(ClientEntity)
            )
            result = self.db_session.execute(stmt).scalar_one_or_none()
            self.db_session.commit()
            return result
        except SQLAlchemyError as e:
            self.db_session.rollback()
            raise e

    def _and_clause(self, organization_id: UUID, id: UUID) -> ColumnElement[bool]:
        return and_(
            ClientEntity.organization_id == organization_id,
            ClientEntity.id == id,
            ClientEntity.deleted_at.is_(None),
        )
