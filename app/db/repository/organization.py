from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import ColumnElement, and_, or_, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import contains_eager, joinedload, selectinload

from app.db.decorator import repository
from app.db.models.certificate import CertificateEntity
from app.db.models.client import ClientEntity
from app.db.models.organization import OrganizationEntity
from app.db.models.scope import ScopeEntity
from app.db.models.source import SourceEntity
from app.db.repository.base import RepositoryBase
from app.models.ura import UraNumber


@repository(OrganizationEntity)
class OrganizationRepository(RepositoryBase):
    def add_one(self, data: OrganizationEntity) -> OrganizationEntity:
        try:
            self.db_session.add(data)
            self.db_session.commit()
            self.db_session.session.refresh(
                data,
                attribute_names=["scopes", "certificates", "sources"],
            )
            return data
        except SQLAlchemyError:
            self.db_session.rollback()
            raise

    def find_one(
        self, id: UUID, with_clients: bool = False, include_deleted: bool = False
    ) -> OrganizationEntity | None:
        stmt = select(OrganizationEntity).options(
            selectinload(OrganizationEntity.scopes), selectinload(OrganizationEntity.sources)
        )
        if include_deleted:
            stmt = stmt.options(selectinload(OrganizationEntity.certificates), selectinload(OrganizationEntity.sources))
        else:
            stmt = stmt.options(
                selectinload(OrganizationEntity.certificates.and_(CertificateEntity.deleted_at.is_(None))),
                selectinload(OrganizationEntity.sources.and_(SourceEntity.deleted_at.is_(None))),
            )

        if not with_clients:
            stmt = stmt.where(self._and_clause(id))
        else:
            stmt = stmt.where(OrganizationEntity.id == id).options(joinedload(OrganizationEntity.clients))

        return self.db_session.execute(stmt).unique().scalar()

    def find_one_by_id(self, id: UUID) -> OrganizationEntity:
        stmt = (
            select(OrganizationEntity)
            .options(
                selectinload(OrganizationEntity.scopes),
                selectinload(OrganizationEntity.certificates.and_(CertificateEntity.deleted_at.is_(None))),
                selectinload(OrganizationEntity.sources.and_(SourceEntity.deleted_at.is_(None))),
            )
            .execution_options(populate_existing=True)
        )

        return self.db_session.execute(stmt).unique().scalar_one()

    def exists(self, id: UUID) -> bool:
        stmt = select(select(OrganizationEntity.id).where(self._and_clause(id)).exists())
        return bool(self.db_session.execute(stmt).scalar())

    def find_one_by_register_id(self, register_id: UraNumber) -> OrganizationEntity | None:
        stmt = select(OrganizationEntity).where(
            and_(
                OrganizationEntity.register_id == register_id,
                OrganizationEntity.deleted_at.is_(None),
            )
        )
        return self.db_session.execute(stmt).scalar()

    def find_one_with_specific_client(self, id: UUID, client_id: UUID) -> OrganizationEntity | None:
        stmt = (
            select(OrganizationEntity)
            .outerjoin(OrganizationEntity.clients)
            .outerjoin(ClientEntity.scopes)
            .where(OrganizationEntity.id == id, ClientEntity.id == client_id)
            .options(
                selectinload(OrganizationEntity.scopes),
                contains_eager(OrganizationEntity.clients).contains_eager(ClientEntity.scopes),
            )
        )
        result = self.db_session.execute(stmt).unique().scalar_one_or_none()
        return result

    def find(
        self,
        id: UUID,
        client_id: UUID | None = None,
        certificate_id: UUID | None = None,
        source_id: UUID | None = None,
    ) -> OrganizationEntity | None:
        load_options = []
        if certificate_id:
            load_options.append(
                selectinload(
                    OrganizationEntity.certificates.and_(
                        CertificateEntity.id == certificate_id, CertificateEntity.deleted_at.is_(None)
                    )
                )
            )

        if source_id:
            load_options.append(
                selectinload(
                    OrganizationEntity.sources.and_(SourceEntity.id == source_id, SourceEntity.deleted_at.is_(None))
                )
            )

        if client_id:
            client_load_option = selectinload(
                OrganizationEntity.clients.and_(ClientEntity.id == client_id, ClientEntity.deleted_at.is_(None))
            ).selectinload(ClientEntity.scopes)
            if certificate_id:
                client_load_option = client_load_option.selectinload(
                    ClientEntity.certificates.and_(
                        CertificateEntity.id == certificate_id, CertificateEntity.deleted_at.is_(None)
                    )
                )

            if source_id:
                client_load_option = client_load_option.selectinload(
                    ClientEntity.sources.and_(SourceEntity.id == source_id, SourceEntity.deleted_at.is_(None))
                )

            load_options.append(client_load_option)

        stmt = select(OrganizationEntity).where(
            and_(OrganizationEntity.id == id, OrganizationEntity.deleted_at.is_(None))
        )
        if load_options:
            stmt = stmt.options(*load_options)

        return self.db_session.execute(stmt).scalar_one_or_none()

    def find_many(
        self,
        external_id: UraNumber | None = None,
        name: str | None = None,
        scopes: list[str] | None = None,
        cert_identifier: str | None = None,
        cert_domain: str | None = None,
        include_deleted: bool = False,
    ) -> Sequence[OrganizationEntity]:
        children_conditions: list[ColumnElement[bool]] = []
        parent_conditions: list[ColumnElement[bool]] = []

        if not include_deleted:
            parent_conditions.append(OrganizationEntity.deleted_at.is_(None))

        if external_id:
            parent_conditions.append(OrganizationEntity.external_id == external_id)
        if name:
            parent_conditions.append(OrganizationEntity.name == name)

        if scopes:
            scopes_conditions = [(ScopeEntity.name == s) for s in scopes]
            children_conditions.append(or_(*scopes_conditions))

        if cert_identifier:
            children_conditions.append(CertificateEntity.organization_identifier == cert_identifier)

        if cert_domain:
            children_conditions.append(CertificateEntity.domain == cert_domain)

        stmt = select(OrganizationEntity)
        if children_conditions:
            stmt = (
                stmt.outerjoin(OrganizationEntity.scopes)
                .outerjoin(OrganizationEntity.certificates.and_(CertificateEntity.deleted_at.is_(None)))
                .outerjoin(OrganizationEntity.sources)
                .options(
                    contains_eager(OrganizationEntity.scopes),
                    contains_eager(OrganizationEntity.certificates),
                    contains_eager(OrganizationEntity.sources),
                )
            ).where(and_(*parent_conditions, *children_conditions))

        else:
            stmt = stmt.options(
                selectinload(OrganizationEntity.scopes),
                selectinload(OrganizationEntity.certificates.and_(CertificateEntity.deleted_at.is_(None))),
                selectinload(OrganizationEntity.sources.and_(SourceEntity.deleted_at.is_(None))),
            ).where(and_(*parent_conditions))

        return self.db_session.execute(stmt).scalars().unique().all()

    def update(self, id: UUID, **kwargs: object) -> OrganizationEntity | None:
        try:
            target = {k: kwargs[k] for k in OrganizationEntity.__table__.columns.keys() if k in kwargs}
            if not target:
                return None
            stmt = update(OrganizationEntity).where(self._and_clause(id)).values(target).returning(OrganizationEntity)
            result = self.db_session.execute(stmt).scalar_one_or_none()
            self.db_session.commit()
            return result
        except SQLAlchemyError:
            self.db_session.rollback()
            raise

    def _and_clause(self, id: UUID) -> ColumnElement[bool]:
        return and_(
            OrganizationEntity.id == id,
            OrganizationEntity.deleted_at.is_(None),
        )
