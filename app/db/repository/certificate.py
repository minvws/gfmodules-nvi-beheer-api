from collections.abc import Sequence
from typing import Any, NamedTuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.decorator import repository
from app.db.models.certificate import CertificateEntity
from app.db.models.client import ClientEntity
from app.db.models.organization import OrganizationEntity
from app.db.repository.base import RepositoryBase
from app.db.repository.contexts.certificate_context import CertificateQueryContext


class CertificateIndexLookup(NamedTuple):
    organization_identifier: str
    domain: str


@repository(CertificateEntity)
class CertificateRepository(RepositoryBase):
    def find_one(self, id: UUID, organization_id: UUID, include_deleted: bool = False) -> CertificateEntity | None:
        stmt = select(CertificateEntity).where(
            CertificateEntity.id == id, CertificateEntity.organization_id == organization_id
        )
        if include_deleted is False:
            stmt = stmt.where(CertificateEntity.deleted_at.is_(None))

        return self.db_session.execute(stmt).scalar()

    def find_many(self, ctx: CertificateQueryContext, include_deleted: bool = False) -> Sequence[CertificateEntity]:
        stmt = select(CertificateEntity)
        cert_filters = ctx.get_conditions()
        if include_deleted is False:
            cert_filters.append(CertificateEntity.deleted_at.is_(None))

        stmt = stmt.where(*cert_filters)

        return self.db_session.execute(stmt).scalars().unique().all()

    def find(self, ctx: CertificateQueryContext, include_deleted: bool = False) -> CertificateEntity | None:
        stmt = select(CertificateEntity)
        options = []

        root_filters = ctx.get_conditions()
        if include_deleted is False:
            root_filters.append(CertificateEntity.deleted_at.is_(None))

        if ctx.organization_ctx:
            org_attr: Any = CertificateEntity.organization
            org_ctx = ctx.organization_ctx
            org_filters = org_ctx.get_conditions()
            if include_deleted is False:
                org_filters.append(OrganizationEntity.deleted_at.is_(None))
            if org_filters:
                org_attr = org_attr.and_(*org_filters)

            options.append(selectinload(org_attr))

        if ctx.client_ctx:
            client_attr: Any = CertificateEntity.clients
            client_ctx = ctx.client_ctx
            client_filters = client_ctx.get_conditions()
            if include_deleted is False:
                client_filters.append(ClientEntity.deleted_at.is_(None))
            if client_filters:
                client_attr = client_attr.and_(*client_filters)

            options.append(selectinload(client_attr))

        if root_filters:
            stmt = stmt.where(*root_filters)
        if options:
            stmt = stmt.options(*options)

        return self.db_session.execute(stmt).unique().scalar_one_or_none()
