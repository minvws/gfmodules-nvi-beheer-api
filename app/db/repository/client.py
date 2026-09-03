import datetime
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import ColumnElement, and_, delete, or_, select, update
from sqlalchemy.exc import DatabaseError, SQLAlchemyError
from sqlalchemy.orm import joinedload, selectinload

from app.db.decorator import repository
from app.db.models.certificate import CertificateEntity
from app.db.models.client import ClientEntity
from app.db.models.client_scope import clients_scopes_association
from app.db.models.organization import OrganizationEntity
from app.db.models.scope import ScopeEntity
from app.db.models.source import SourceEntity
from app.db.repository.base import RepositoryBase
from app.models.oin import Oin
from app.models.ura import UraNumber


@repository(ClientEntity)
class ClientRepository(RepositoryBase):
    def add_one(self, data: ClientEntity) -> ClientEntity:
        try:
            self.db_session.add(data)
            self.db_session.commit()
            self.db_session.session.refresh(data, attribute_names=["scopes", "certificates", "sources"])
            return data
        except SQLAlchemyError:
            self.db_session.rollback()
            raise

    def find_one(self, organization_id: UUID, id: UUID) -> ClientEntity | None:
        stmt = (
            select(ClientEntity).options(selectinload(ClientEntity.scopes)).where(self._and_clause(organization_id, id))
        )

        return self.db_session.execute(stmt).scalar_one_or_none()

    def find(
        self,
        id: UUID,
        organization_id: UUID | None = None,
        certificate_id: UUID | None = None,
        source_id: UUID | None = None,
    ) -> ClientEntity | None:
        load_options = []
        if certificate_id:
            load_options.append(
                selectinload(
                    ClientEntity.certificates.and_(
                        CertificateEntity.id == certificate_id, CertificateEntity.deleted_at.is_(None)
                    )
                )
            )

        if source_id:
            load_options.append(
                selectinload(ClientEntity.sources.and_(SourceEntity.id == source_id, SourceEntity.deleted_at.is_(None)))
            )

        stmt = select(ClientEntity).where(
            ClientEntity.id == id,
        )

        if load_options:
            stmt = stmt.options(*load_options)

        return self.db_session.execute(stmt).scalar_one_or_none()

    def exists(self, organization_id: UUID, id: UUID) -> bool:
        stmt = select(select(ClientEntity.id).where(self._and_clause(organization_id, id)).exists())
        return bool(self.db_session.execute(stmt).scalar())

    def get_by_credentials(self, common_name: str, oin: Oin, org_ura: UraNumber) -> ClientEntity | None:
        stmt = (
            select(ClientEntity)
            .join(
                OrganizationEntity,
                ClientEntity.organization_id == OrganizationEntity.id,
            )
            .where(
                and_(
                    ClientEntity.common_name == common_name,
                    ClientEntity.oin == oin,
                    OrganizationEntity.register_id == org_ura,
                    OrganizationEntity.deleted_at.is_(None),
                    ClientEntity.deleted_at.is_(None),
                )
            )
            .options(joinedload(ClientEntity.organization))
        )
        return self.db_session.execute(stmt).scalar()

    def find_many(
        self,
        organization_id: UUID,
        oin: Oin | None = None,
        common_name: str | None = None,
        source_id: str | None = None,
        scopes: list[str] | None = None,
        include_deleted: bool = False,
    ) -> Sequence[ClientEntity]:
        stmt = select(ClientEntity).options(selectinload(ClientEntity.scopes))
        conditions: list[ColumnElement[bool]] = [ClientEntity.organization_id == organization_id]
        if not include_deleted:
            conditions.append(ClientEntity.deleted_at.is_(None))
        if oin:
            conditions.append(ClientEntity.oin == oin)
        if common_name:
            conditions.append(ClientEntity.common_name == common_name)
        if source_id:
            conditions.append(ClientEntity.source_id == source_id)
        if scopes:
            stmt = stmt.join(ClientEntity.scopes)
            scope_conditions = [(ScopeEntity.name == s) for s in scopes]
            conditions.append(or_(*scope_conditions))

        stmt = stmt.where(and_(*conditions))
        return self.db_session.execute(stmt).scalars().unique().all()

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

    def delete_one(self, id: UUID) -> None:
        try:
            client_stmt = update(ClientEntity).where(ClientEntity.id == id).values(deleted_at=datetime.datetime.now())
            self.db_session.session.execute(client_stmt)

            scope_stmt = delete(clients_scopes_association).where(clients_scopes_association.c.client_id == id)
            self.db_session.session.execute(scope_stmt)

            self.db_session.commit()
        except DatabaseError as e:
            self.db_session.rollback()
            raise e

    def _and_clause(self, organization_id: UUID, id: UUID) -> ColumnElement[bool]:
        return and_(
            ClientEntity.organization_id == organization_id,
            ClientEntity.id == id,
            ClientEntity.deleted_at.is_(None),
        )
