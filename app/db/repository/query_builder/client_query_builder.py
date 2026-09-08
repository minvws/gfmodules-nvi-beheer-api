from typing import Self
from uuid import UUID

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import contains_eager, selectinload

from app.db.models.certificate import CertificateEntity
from app.db.models.client import ClientEntity
from app.db.models.scope import ScopeEntity
from app.db.models.source import SourceEntity
from app.db.repository.query_builder.context.client_context import (
    ClientCertificateQueryContext,
    ClientQueryContext,
    ClientSourceQueryContext,
)
from app.db.repository.query_builder.data import LoadStrategy


class ClientQueryBuilder:
    def __init__(self, load_strategy: LoadStrategy = LoadStrategy.SELECTIN_LOAD, include_deleted: bool = False) -> None:
        self._stmt = select(ClientEntity)
        self._load_strategy: LoadStrategy = load_strategy
        self._include_deleted: bool = include_deleted

    def apply_context(self, ctx: ClientQueryContext) -> Self:
        self.include_scopes(ctx.scopes)

        if ctx.id:
            self.with_id(ctx.id)

        if ctx.organization_id:
            self.with_organization_id(ctx.organization_id)

        if ctx.name:
            self.with_name(ctx.name)

        if ctx.description:
            self.with_description(ctx.description)

        if ctx.certificate_ctx:
            self.include_certificate(ctx.certificate_ctx)

        if ctx.source_ctx:
            self.include_sources(ctx.source_ctx)

        return self

    def with_id(self, id: UUID | None) -> Self:
        if id is None:
            return self

        self._stmt = self._stmt.where(ClientEntity.id == id)
        return self

    def with_organization_id(self, id: UUID | None) -> Self:
        if id is None:
            return self

        self._stmt = self._stmt.where(ClientEntity.organization_id == id)
        return self

    def with_name(self, name: str | None) -> Self:
        if name is None:
            return self

        self._stmt = self._stmt.where(ClientEntity.name == name)
        return self

    def with_description(self, description: str | None) -> Self:
        if description is None:
            return self
        self._stmt = self._stmt.where(ClientEntity.description == description)
        return self

    def include_scopes(self, scopes: list[str] | None = None) -> Self:
        match self._load_strategy:
            case LoadStrategy.SELECTIN_LOAD:
                self._selectinload_scopes(scopes)

            case LoadStrategy.OUTERJOIN_LOAD:
                self._joinload_scopes(scopes)

        return self

    def _selectinload_scopes(self, scopes: list[str] | None = None) -> Self:
        attr = ClientEntity.scopes
        if scopes:
            attr = attr.and_(or_(*[ScopeEntity.name == s for s in scopes]))

        self._stmt = self._stmt.options(selectinload(attr))
        return self

    def _joinload_scopes(self, scopes: list[str] | None = None) -> Self:
        self._stmt = self._stmt.outerjoin(ClientEntity.scopes).options(contains_eager(ClientEntity.scopes))

        if scopes:
            self._stmt = self._stmt.where(or_(*[ScopeEntity.name == s for s in scopes]))

        return self

    def include_certificate(self, ctx: ClientCertificateQueryContext) -> Self:
        match self._load_strategy:
            case LoadStrategy.OUTERJOIN_LOAD:
                self._joinload_cert(ctx)

            case LoadStrategy.SELECTIN_LOAD:
                self._selectinload_cert(ctx)

        return self

    def _selectinload_cert(self, ctx: ClientCertificateQueryContext) -> Self:
        attr = ClientEntity.certificates
        conditions = []

        if ctx.id:
            conditions.append(CertificateEntity.id == ctx.id)

        if ctx.domain:
            conditions.append(CertificateEntity.domain == ctx.domain)

        if ctx.organization_identifier:
            conditions.append(CertificateEntity.organization_identifier == ctx.organization_identifier)

        if conditions:
            attr = attr.and_(*conditions)

        self._stmt = self._stmt.options(selectinload(attr))
        return self

    def _joinload_cert(
        self,
        ctx: ClientCertificateQueryContext,
    ) -> Self:
        attr = ClientEntity.certificates
        conditions = []

        self._stmt = self._stmt.outerjoin(attr).options(contains_eager(ClientEntity.certificates))

        if ctx.id:
            conditions.append(CertificateEntity.id == ctx.id)

        if ctx.domain:
            conditions.append(CertificateEntity.domain == ctx.domain)

        if ctx.organization_identifier:
            conditions.append(CertificateEntity.organization_identifier == ctx.organization_identifier)

        if conditions:
            self._stmt = self._stmt.where(*conditions)

        return self

    def include_sources(self, ctx: ClientSourceQueryContext) -> Self:
        match self._load_strategy:
            case LoadStrategy.OUTERJOIN_LOAD:
                self._joinload_sources(ctx)
            case LoadStrategy.SELECTIN_LOAD:
                self._selectinload_sources(ctx)
        return self

    def _selectinload_sources(self, ctx: ClientSourceQueryContext) -> Self:
        attr = ClientEntity.sources
        conditions = []
        if ctx.id:
            conditions.append(SourceEntity.id == ctx.id)

        if ctx.source_id:
            conditions.append(SourceEntity.source_id == ctx.source_id)

        if ctx.name:
            conditions.append(SourceEntity.name == ctx.name)

        if conditions:
            attr = attr.and_(*conditions)

        self._stmt = self._stmt.options(selectinload(attr))
        return self

    def _joinload_sources(self, ctx: ClientSourceQueryContext) -> Self:
        attr = ClientEntity.sources
        conditions = []

        if ctx.id:
            conditions.append(SourceEntity.id == ctx.id)
        if ctx.source_id:
            conditions.append(SourceEntity.source_id == ctx.source_id)

        if ctx.name:
            conditions.append(SourceEntity.name == ctx.name)

        self._stmt = self._stmt.outerjoin(attr).options(contains_eager(ClientEntity.sources))

        if conditions:
            self._stmt = self._stmt.where(*conditions)

        return self

    def build(self) -> Select[tuple[ClientEntity]]:
        if self._include_deleted is False:
            self._stmt = self._stmt.where(ClientEntity.deleted_at.is_(None))
        return self._stmt
