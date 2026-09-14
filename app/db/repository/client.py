from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from app.db.decorator import repository
from app.db.models.certificate import CertificateEntity
from app.db.models.client import ClientEntity
from app.db.models.organization import OrganizationEntity
from app.db.models.source import SourceEntity
from app.db.repository.base import RepositoryBase
from app.db.repository.contexts.client_context import (
    ClientQueryContext,
)
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

    def find_one(self, id: UUID, organization_id: UUID, include_deleted: bool = False) -> ClientEntity | None:
        stmt = (
            select(ClientEntity)
            .options(
                selectinload(ClientEntity.scopes),
                selectinload(ClientEntity.sources),
                selectinload(ClientEntity.certificates),
            )
            .where(and_(ClientEntity.id == id, ClientEntity.organization_id == organization_id))
        )
        if include_deleted is False:
            stmt = stmt.where(ClientEntity.deleted_at.is_(None))

        return self.db_session.execute(stmt).scalar()

    def find_many(self, ctx: ClientQueryContext, include_deleted: bool = False) -> Sequence[ClientEntity]:
        stmt = select(ClientEntity)
        crt_attr = (
            ClientEntity.certificates
            if include_deleted
            else ClientEntity.certificates.and_(CertificateEntity.deleted_at.is_(None))
        )
        src_attr = (
            ClientEntity.sources if include_deleted else ClientEntity.sources.and_(SourceEntity.deleted_at.is_(None))
        )

        stmt = stmt.options(selectinload(ClientEntity.scopes), selectinload(crt_attr), selectinload(src_attr))

        root_filters = ctx.get_conditions()
        if include_deleted is False:
            root_filters.append(ClientEntity.deleted_at.is_(None))

        if root_filters:
            stmt = stmt.where(*root_filters)

        if ctx.certificate_ctx:
            cert_ctx = ctx.certificate_ctx
            crt_filters = cert_ctx.get_conditions()

            if crt_filters:
                if include_deleted is False:
                    crt_filters.append(CertificateEntity.deleted_at.is_(None))
                stmt = stmt.where(ClientEntity.certificates.any(and_(*crt_filters)))

        if ctx.source_ctx:
            src_ctx = ctx.source_ctx
            src_filters = src_ctx.get_conditions()

            if src_filters:
                if include_deleted is False:
                    src_filters.append(SourceEntity.deleted_at.is_(None))
                stmt = stmt.where(ClientEntity.sources.any(and_(*src_filters)))

        return self.db_session.execute(stmt).scalars().unique().all()

    def find(self, ctx: ClientQueryContext, include_deleted: bool = False) -> ClientEntity | None:
        stmt = select(ClientEntity)

        options = [selectinload(ClientEntity.scopes)]

        root_filters = ctx.get_conditions()
        if include_deleted is False:
            root_filters.append(ClientEntity.deleted_at.is_(None))

        if root_filters:
            stmt = stmt.where(*root_filters)

        if ctx.certificate_ctx:
            cert_attr: Any = ClientEntity.certificates
            crt_ctx = ctx.certificate_ctx
            crt_filters = crt_ctx.get_conditions()
            if include_deleted is False:
                crt_filters.append(CertificateEntity.deleted_at.is_(None))

            if crt_filters:
                cert_attr = cert_attr.and_(*crt_filters)

            options.append(selectinload(cert_attr))

        if ctx.source_ctx:
            src_attr: Any = ClientEntity.sources
            src_ctx = ctx.source_ctx
            src_filters = src_ctx.get_conditions()
            if include_deleted is False:
                src_filters.append(SourceEntity.deleted_at.is_(None))

            if src_filters:
                src_attr = src_attr.and_(*src_filters)

            options.append(selectinload(src_attr))

        stmt = stmt.options(*options)
        return self.db_session.execute(stmt).scalar_one_or_none()

    def get_by_credentials(
        self, id: UUID, domain: str, organization_identifier: Oin, external_id: UraNumber, source_id: str | None = None
    ) -> ClientEntity | None:
        source_attr = (
            ClientEntity.sources.and_(SourceEntity.source_id == source_id) if source_id else ClientEntity.sources
        )
        stmt = (
            select(ClientEntity)
            .options(
                selectinload(ClientEntity.scopes),
                selectinload(
                    ClientEntity.certificates.and_(
                        CertificateEntity.organization_identifier == organization_identifier,
                        CertificateEntity.domain == domain,
                    )
                ),
                selectinload(source_attr),
                selectinload(ClientEntity.organization.and_(OrganizationEntity.external_id == external_id)),
            )
            .where(ClientEntity.id == id, ClientEntity.deleted_at.is_(None))
        )

        return self.db_session.execute(stmt).scalars().unique().one_or_none()
