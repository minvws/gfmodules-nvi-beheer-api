from dataclasses import dataclass
from typing import Any, Self
from uuid import UUID

from app.db.models.certificate import CertificateEntity
from app.db.models.client import ClientEntity
from app.db.models.organization import OrganizationEntity
from app.db.models.scope import ScopeEntity
from app.db.models.source import SourceEntity
from app.db.repository.contexts.data import (
    CertificateQueryContextBase,
    ClientQueryContextBase,
    OrganizationQueryContextBase,
    SourceQueryContextBase,
)


@dataclass()
class OrganizationCertificateQueryContext(CertificateQueryContextBase):
    def get_conditions(self) -> list[Any]:
        crt_filters = []
        if self.id:
            crt_filters.append(CertificateEntity.id == self.id)

        if self.organization_identifier:
            crt_filters.append(CertificateEntity.organization_identifier == self.organization_identifier)

        if self.domain:
            crt_filters.append(CertificateEntity.domain == self.domain)

        return crt_filters


@dataclass()
class OrganizationSourceQueryContext(SourceQueryContextBase):
    def get_conditions(self) -> list[Any]:
        src_filters = []
        if self.id:
            src_filters.append(SourceEntity.id == self.id)

        if self.source_id:
            src_filters.append(SourceEntity.source_id == self.source_id)

        if self.name:
            src_filters.append(SourceEntity.name == self.name)

        return src_filters


@dataclass()
class OrganizationClientQueryContext(ClientQueryContextBase):
    scopes: list[str] | None = None
    certificate_ctx: OrganizationCertificateQueryContext | None = None
    source_ctx: OrganizationSourceQueryContext | None = None
    include_scopes: bool = True

    @classmethod
    def default(cls) -> Self:
        cert_ctx = OrganizationCertificateQueryContext.default()
        src_ctx = OrganizationSourceQueryContext.default()
        return cls(
            certificate_ctx=cert_ctx,
            source_ctx=src_ctx,
        )

    def get_conditions(self) -> list[Any]:
        client_filters = []
        if self.id:
            client_filters.append(ClientEntity.id == self.id)

        if self.name:
            client_filters.append(ClientEntity.name == self.name)

        if self.scopes:
            client_filters.append(ClientEntity.scopes.any(ScopeEntity.name.in_(self.scopes)))

        return client_filters


@dataclass()
class OrganizationQueryContext(OrganizationQueryContextBase):
    id: UUID | None = None
    scopes: list[str] | None = None
    client_ctx: OrganizationClientQueryContext | None = None
    certificate_ctx: OrganizationCertificateQueryContext | None = None
    source_ctx: OrganizationSourceQueryContext | None = None

    def get_conditions(self) -> list[Any]:
        conditions = []
        if self.id:
            conditions.append(OrganizationEntity.id == self.id)

        if self.external_id:
            conditions.append(OrganizationEntity.external_id == self.external_id)

        if self.name:
            conditions.append(OrganizationEntity.name == self.name)

        if self.scopes:
            conditions.append(OrganizationEntity.scopes.any(ScopeEntity.name.in_(self.scopes)))

        return conditions
