from typing import Self
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import contains_eager, selectinload

from app.db.models.certificate import CertificateEntity
from app.db.models.client import ClientEntity
from app.db.models.organization import OrganizationEntity
from app.db.repository.query_builder.context.certificate_context import (
    CertificateClientQueryContext,
    CertificateOrganizationQueryContext,
    CertificateQueryContext,
    CertificateRelations,
)
from app.db.repository.query_builder.context.data import LoadStrategy
from app.models.oin import Oin


class CertificateQueryBuilder:
    def __init__(self, load_strategy: LoadStrategy = LoadStrategy.SELECTIN_LOAD, include_deleted: bool = False) -> None:
        self._stmt = select(CertificateEntity)
        self._load_strategy: LoadStrategy = load_strategy
        self._include_deleted: bool = include_deleted

    def apply_context(self, ctx: CertificateQueryContext) -> Self:
        if ctx.id:
            self.with_id(ctx.id)

        if ctx.organization_identifier:
            self.with_organization_identifier(ctx.organization_identifier)

        if ctx.domain:
            self.with_domain(ctx.domain)

        for rel in ctx.include:
            match rel:
                case CertificateRelations.CLIENTS:
                    client_ctx = ctx.client_ctx if ctx.client_ctx else CertificateClientQueryContext.default()
                    self.include_clients(client_ctx)

                case CertificateRelations.ORGANIZATION:
                    org_ctx = (
                        ctx.organization_ctx if ctx.organization_ctx else CertificateOrganizationQueryContext.default()
                    )
                    self.include_organization(org_ctx)

        return self

    def with_id(self, id: UUID | None) -> Self:
        if id is None:
            return self

        self._stmt = self._stmt.where(CertificateEntity.id == id)
        return self

    def with_organization_id(self, organization_id: UUID | None) -> Self:
        if organization_id is None:
            return self

        self._stmt = self._stmt.where(CertificateEntity.organization_id == organization_id)
        return self

    def with_organization_identifier(self, org_identifier: Oin | None) -> Self:
        if org_identifier is None:
            return self

        self._stmt = self._stmt.where(CertificateEntity.organization_identifier == org_identifier)
        return self

    def with_domain(self, domain: str | None) -> Self:
        if domain is None:
            return self

        self._stmt = self._stmt.where(CertificateEntity.domain == domain)
        return self

    def include_organization(self, ctx: CertificateOrganizationQueryContext) -> Self:
        match self._load_strategy:
            case LoadStrategy.SELECTIN_LOAD:
                self._selectinload_organization(ctx)
            case LoadStrategy.OUTERJOIN_LOAD:
                self._joinload_organization(ctx)

        return self

    def _selectinload_organization(self, ctx: CertificateOrganizationQueryContext) -> Self:
        attr = CertificateEntity.organization
        conditions = []
        if ctx.id:
            conditions.append(OrganizationEntity.id == ctx.id)

        if ctx.name:
            conditions.append(OrganizationEntity.name == ctx.name)

        if self._include_deleted is False:
            conditions.append(OrganizationEntity.deleted_at.is_(None))

        if conditions:
            attr = attr.and_(*conditions)
        self._stmt = self._stmt.options(selectinload(attr))
        return self

    def _joinload_organization(self, ctx: CertificateOrganizationQueryContext) -> Self:
        attr = CertificateEntity.organization
        self._stmt = self._stmt.outerjoin(attr).options(contains_eager(attr))

        conditions = []
        if ctx.id:
            conditions.append(OrganizationEntity.id == ctx.id)

        if ctx.name:
            conditions.append(OrganizationEntity.name == ctx.name)

        if ctx.external_id:
            conditions.append(OrganizationEntity.external_id == ctx.external_id)

        if self._include_deleted is False:
            conditions.append(OrganizationEntity.deleted_at.is_(None))

        if conditions:
            self._stmt = self._stmt.where(*conditions)

        return self

    def include_clients(self, ctx: CertificateClientQueryContext) -> Self:
        match self._load_strategy:
            case LoadStrategy.SELECTIN_LOAD:
                self._selectinload_clients(ctx)

            case LoadStrategy.OUTERJOIN_LOAD:
                self._joinload_clients(ctx)

        return self

    def _selectinload_clients(self, ctx: CertificateClientQueryContext) -> Self:
        attr = CertificateEntity.clients
        conditions = []

        if ctx.id:
            conditions.append(ClientEntity.id == ctx.id)

        if ctx.name:
            conditions.append(ClientEntity.name == ctx.name)

        if ctx.description:
            conditions.append(ClientEntity.description == ctx.description)

        if self._include_deleted is False:
            conditions.append(ClientEntity.deleted_at.is_(None))

        if conditions:
            attr = attr.and_(*conditions)

        self._stmt = self._stmt.options(selectinload(attr))
        return self

    def _joinload_clients(self, ctx: CertificateClientQueryContext) -> Self:
        attr = CertificateEntity.clients
        conditions = []
        if ctx.id:
            conditions.append(ClientEntity.id == ctx.id)

        if ctx.name:
            conditions.append(ClientEntity.name == ctx.name)

        if ctx.description:
            conditions.append(ClientEntity.description == ctx.description)

        if self._include_deleted is False:
            conditions.append(ClientEntity.deleted_at.is_(None))

        self._stmt = self._stmt.outerjoin(attr).options(contains_eager(attr))
        if conditions:
            self._stmt = self._stmt.where(*conditions)

        return self

    def build(self) -> Select[tuple[CertificateEntity]]:
        if self._include_deleted is False:
            self._stmt = self._stmt.where(CertificateEntity.deleted_at.is_(None))

        return self._stmt
