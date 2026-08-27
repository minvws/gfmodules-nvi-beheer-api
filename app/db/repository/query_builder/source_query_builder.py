from typing import Self
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import contains_eager, selectinload

from app.db.models.certificate import CertificateEntity
from app.db.models.client import ClientEntity
from app.db.models.organization import OrganizationEntity
from app.db.models.source import SourceEntity
from app.db.repository.query_builder.context.source_context import (
    SourceClientQueryContext,
    SourceOrganizationQueryContext,
    SourceQueryContext,
    SourceRelations,
)
from app.db.repository.query_builder.data import LoadStrategy


class SourceQueryBuilder:
    def __init__(self, load_strategy: LoadStrategy = LoadStrategy.SELECTIN_LOAD, include_deleted: bool = False) -> None:
        self._stmt = select(SourceEntity)
        self._load_strategy: LoadStrategy = load_strategy
        self._include_deleted: bool = include_deleted

    def apply_context(self, ctx: SourceQueryContext) -> Self:
        if ctx.id:
            self.with_id(ctx.id)

        if ctx.source_id:
            self.with_source_id(ctx.source_id)

        if ctx.name:
            self.with_name(ctx.name)

        for rel in ctx.include:
            match rel:
                case SourceRelations.ORGANIZATION:
                    org_ctx = ctx.organization_ctx if ctx.organization_ctx else SourceOrganizationQueryContext.default()
                    self.include_organization(org_ctx)

                case SourceRelations.CLIENTS:
                    client_ctx = ctx.client_ctx if ctx.client_ctx else SourceClientQueryContext.default()
                    self.include_clients(client_ctx)

        return self

    def with_id(self, id: UUID | None) -> Self:
        if id is None:
            return self

        self._stmt = self._stmt.where(SourceEntity.id == id)
        return self

    def with_source_id(self, source_id: str | None) -> Self:
        if source_id is None:
            return self

        self._stmt = self._stmt.where(SourceEntity.source_id == source_id)
        return self

    def with_name(self, name: str | None) -> Self:
        if name is None:
            return self

        self._stmt = self._stmt.where(SourceEntity.name == name)
        return self

    def include_organization(self, ctx: SourceOrganizationQueryContext) -> Self:
        match self._load_strategy:
            case LoadStrategy.SELECTIN_LOAD:
                self._selecintload_organizations(ctx)
            case LoadStrategy.OUTERJOIN_LOAD:
                self._joinload_organizations(ctx)

        return self

    def _selecintload_organizations(self, ctx: SourceOrganizationQueryContext) -> Self:
        attr = SourceEntity.organization
        conditions = []

        if ctx.id:
            conditions.append(OrganizationEntity.id == ctx.id)

        if ctx.external_id:
            conditions.append(OrganizationEntity.external_id == ctx.external_id)

        if ctx.name:
            conditions.append(OrganizationEntity.name == ctx.name)

        if self._include_deleted is False:
            conditions.append(OrganizationEntity.deleted_at.is_(None))

        if conditions:
            attr = attr.and_(*conditions)

        self._stmt = self._stmt.options(selectinload(attr))
        return self

    def _joinload_organizations(self, ctx: SourceOrganizationQueryContext) -> Self:
        attr = SourceEntity.organization
        self._stmt = self._stmt.outerjoin(attr).options(contains_eager(attr))

        conditions = []

        if self._include_deleted is False:
            conditions.append(OrganizationEntity.deleted_at.is_(None))
        if ctx.id:
            conditions.append(OrganizationEntity.id == ctx.id)

        if ctx.external_id:
            conditions.append(OrganizationEntity.external_id == ctx.external_id)

        if ctx.name:
            conditions.append(OrganizationEntity.name == ctx.name)

        if self._include_deleted is False:
            conditions.append(OrganizationEntity.deleted_at.is_(None))

        if conditions:
            self._stmt = self._stmt.where(*conditions)

        return self

    def include_clients(self, ctx: SourceClientQueryContext) -> Self:
        match self._load_strategy:
            case LoadStrategy.SELECTIN_LOAD:
                self._selectinload_clients(ctx)
            case LoadStrategy.OUTERJOIN_LOAD:
                self._joinload_clients(ctx)

        return self

    def _selectinload_clients(self, ctx: SourceClientQueryContext) -> Self:
        attr = CertificateEntity.clients
        conditions = []

        if self._include_deleted:
            conditions.append(ClientEntity.deleted_at.is_(None))

        if ctx.id:
            conditions.append(ClientEntity.id == ctx.id)

        if ctx.name:
            conditions.append(ClientEntity.name == ctx.name)

        if ctx.description:
            conditions.append(ClientEntity.description)

        if conditions:
            attr = attr.and_(*conditions)

        self._stmt = self._stmt.options(selectinload(attr))
        return self

    def _joinload_clients(self, ctx: SourceClientQueryContext) -> Self:
        attr = CertificateEntity.clients
        self._stmt = self._stmt.outerjoin(attr).options(contains_eager(attr))

        conditions = []
        if self._include_deleted is False:
            conditions.append(ClientEntity.deleted_at.is_(None))

        if ctx.id:
            conditions.append(ClientEntity.id == ctx.id)

        if ctx.name:
            conditions.append(ClientEntity.name == ctx.name)

        if ctx.description:
            conditions.append(ClientEntity.description == ctx.description)

        if conditions:
            self._stmt = self._stmt.where(*conditions)

        return self

    def build(self) -> Select[tuple[SourceEntity]]:
        if self._include_deleted is False:
            self._stmt = self._stmt.where(SourceEntity.deleted_at.is_(None))

        return self._stmt
