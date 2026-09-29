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
from app.db.repository.contexts.organization_context import (
    OrganizationQueryContext,
)
from app.models.ura import UraNumber


@repository(OrganizationEntity)
class OrganizationRepository(RepositoryBase):
    def add_one(self, data: OrganizationEntity) -> OrganizationEntity:
        try:
            self.db_session.add(data)
            self.db_session.commit()
            return data
        except SQLAlchemyError:
            self.db_session.rollback()
            raise

    def find_one(
        self,
        id: UUID,
        include_deleted: bool = False,
    ) -> OrganizationEntity | None:
        stmt = (
            select(OrganizationEntity)
            .options(
                selectinload(OrganizationEntity.scopes),
                selectinload(OrganizationEntity.certificates),
                selectinload(OrganizationEntity.sources),
                selectinload(OrganizationEntity.clients).selectinload(ClientEntity.scopes),
                selectinload(OrganizationEntity.clients).selectinload(ClientEntity.certificates),
                selectinload(OrganizationEntity.clients).selectinload(ClientEntity.sources),
            )
            .where(OrganizationEntity.id == id)
        )
        if include_deleted is False:
            stmt = stmt.where(OrganizationEntity.deleted_at.is_(None))

        return self.db_session.execute(stmt).unique().scalar()

    def exists(self, id: UUID) -> bool:
        stmt = select(
            select(OrganizationEntity.id)
            .where(
                and_(OrganizationEntity.id == id, OrganizationEntity.deleted_at.is_(None)),
            )
            .exists()
        )
        return bool(self.db_session.execute(stmt).scalar())

    def exsits_by_external_id(self, external_id: UraNumber) -> bool:
        stmt = select(
            select(OrganizationEntity.external_id)
            .where(
                and_(OrganizationEntity.external_id == external_id, OrganizationEntity.deleted_at.is_(None)),
            )
            .exists()
        )
        return bool(self.db_session.execute(stmt).scalar())

    def find(
        self,
        ctx: OrganizationQueryContext,
        include_deleted: bool = False,
    ) -> OrganizationEntity | None:
        """
        Will automatically load children once a parameter is present.
        """
        stmt = select(OrganizationEntity)

        options = [selectinload(OrganizationEntity.scopes)]

        root_filters = ctx.get_conditions()
        if include_deleted is False:
            root_filters.append(OrganizationEntity.deleted_at.is_(None))

        if root_filters:
            stmt = stmt.where(*root_filters)

        if ctx.certificate_ctx:
            cert_attr: Any = OrganizationEntity.certificates
            crt_ctx = ctx.certificate_ctx
            crt_filters = crt_ctx.get_conditions()

            if include_deleted is False:
                crt_filters.append(CertificateEntity.deleted_at.is_(None))

            if crt_filters:
                cert_attr = cert_attr.and_(*crt_filters)

            options.append(selectinload(cert_attr))

        if ctx.source_ctx:
            src_attr: Any = OrganizationEntity.sources
            src_ctx = ctx.source_ctx

            src_filters = src_ctx.get_conditions()
            if include_deleted is False:
                src_filters.append(SourceEntity.deleted_at.is_(None))

            if src_filters:
                src_attr = src_attr.and_(*src_filters)

            options.append(selectinload(src_attr))

        if ctx.client_ctx:
            client_attr: Any = OrganizationEntity.clients
            client_ctx = ctx.client_ctx

            client_filters = client_ctx.get_conditions()
            if include_deleted is False:
                client_filters.append(ClientEntity.deleted_at.is_(None))

            if client_filters:
                client_attr = client_attr.and_(*client_filters)

            options.append(selectinload(client_attr).selectinload(ClientEntity.scopes))

            if client_ctx.certificate_ctx:
                client_crt_ctx = client_ctx.certificate_ctx
                client_crt_attr: Any = ClientEntity.certificates

                client_crt_filters = client_crt_ctx.get_conditions()
                if include_deleted is False:
                    client_crt_filters.append(CertificateEntity.deleted_at.is_(None))

                if client_crt_filters:
                    client_crt_attr = client_crt_attr.and_(*client_crt_filters)

                options.append(selectinload(client_attr).selectinload(client_crt_attr))

            if client_ctx.source_ctx:
                client_src_ctx = client_ctx.source_ctx
                client_src_attr: Any = ClientEntity.sources
                client_src_filters = client_src_ctx.get_conditions()

                if client_src_filters:
                    if include_deleted is False:
                        client_src_filters.append(SourceEntity.deleted_at.is_(None))
                    client_src_attr = client_src_attr.and_(*client_src_filters)

                options.append(selectinload(client_attr).selectinload(client_src_attr))

        stmt = stmt.options(*options)
        return self.db_session.execute(stmt).unique().scalar_one_or_none()

    def find_many(
        self,
        ctx: OrganizationQueryContext,
        include_deleted: bool = False,
    ) -> Sequence[OrganizationEntity]:
        stmt = select(OrganizationEntity)
        crt_attr = (
            OrganizationEntity.certificates
            if include_deleted
            else OrganizationEntity.certificates.and_(CertificateEntity.deleted_at.is_(None))
        )
        src_attr = (
            OrganizationEntity.sources
            if include_deleted
            else OrganizationEntity.sources.and_(SourceEntity.deleted_at.is_(None))
        )
        client_attr = (
            OrganizationEntity.clients
            if include_deleted
            else OrganizationEntity.clients.and_(ClientEntity.deleted_at.is_(None))
        )

        stmt = stmt.options(
            selectinload(OrganizationEntity.scopes),
            selectinload(crt_attr),
            selectinload(src_attr),
            selectinload(client_attr).selectinload(ClientEntity.scopes),
            selectinload(client_attr).selectinload(ClientEntity.certificates),
            selectinload(client_attr).selectinload(ClientEntity.sources),
        )

        root_filter = ctx.get_conditions()
        if include_deleted is False:
            root_filter.append(OrganizationEntity.deleted_at.is_(None))

        if root_filter:
            stmt = stmt.where(*root_filter)

        if ctx.certificate_ctx:
            crt_ctx = ctx.certificate_ctx
            crt_filters = crt_ctx.get_conditions()
            if crt_filters:
                if include_deleted is False:
                    crt_filters.append(CertificateEntity.deleted_at.is_(None))
                stmt = stmt.where(OrganizationEntity.certificates.any(and_(*crt_filters)))

        if ctx.source_ctx:
            src_ctx = ctx.source_ctx
            src_filters = src_ctx.get_conditions()
            if src_filters:
                if include_deleted is False:
                    src_filters.append(SourceEntity.deleted_at.is_(None))
                stmt = stmt.where(OrganizationEntity.sources.any(and_(*src_filters)))

        if ctx.client_ctx:
            client_ctx = ctx.client_ctx
            client_filters = client_ctx.get_conditions()
            if include_deleted is False:
                client_filters.append(ClientEntity.deleted_at.is_(None))

            if client_ctx.certificate_ctx:
                client_crt_ctx = client_ctx.certificate_ctx
                client_crt_filters = client_crt_ctx.get_conditions()
                if client_crt_filters:
                    client_filters.append(ClientEntity.certificates.any(and_(*client_crt_filters)))

            if client_ctx.source_ctx:
                client_src_ctx = client_ctx.source_ctx
                client_src_filters = client_src_ctx.get_conditions()
                if client_src_filters:
                    client_filters.append(ClientEntity.sources.any(and_(*client_src_filters)))

            if client_filters:
                stmt = stmt.where(OrganizationEntity.clients.any(and_(*client_filters)))

        return self.db_session.execute(stmt).scalars().unique().all()
