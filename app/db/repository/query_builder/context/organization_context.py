from dataclasses import dataclass
from typing import Any, Self
from uuid import UUID

from app.db.repository.query_builder.context.data import (
    CertificateQueryContextBase,
    ClientQueryContextBase,
    OrganizationQueryContextBase,
    SourceQueryContextBase,
)


@dataclass()
class OrganizationCertificateQueryContext(CertificateQueryContextBase):
    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "organization_identifier": self.organization_identifier, "domain": self.domain}


@dataclass()
class OrganizationSourceQueryContext(SourceQueryContextBase):
    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "source_id": self.source_id, "name": self.name}


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


@dataclass()
class OrganizationQueryContext(OrganizationQueryContextBase):
    id: UUID | None = None
    scopes: list[str] | None = None
    client_ctx: OrganizationClientQueryContext | None = None
    certificate_ctx: OrganizationCertificateQueryContext | None = None
    source_ctx: OrganizationSourceQueryContext | None = None
