from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Self

from app.db.repository.query_builder.context.data import (
    CertificateQueryContextBase,
    ClientQueryContextBase,
    OrganizationQueryContextBase,
    SourceQueryContextBase,
)


class OrganizationRelations(Enum):
    CLIENTS = auto()
    CERTIFICATES = auto()
    SOURCES = auto()
    SCOPES = auto()


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
    scopes: list[str] | None = None
    client_ctx: OrganizationClientQueryContext | None = None
    certificate_ctx: OrganizationCertificateQueryContext | None = None
    source_ctx: OrganizationSourceQueryContext | None = None

    @property
    def includes(self) -> set[OrganizationRelations]:
        relations = {OrganizationRelations.SCOPES}
        if self.source_ctx:
            relations.add(OrganizationRelations.SOURCES)

        if self.certificate_ctx:
            relations.add(OrganizationRelations.CERTIFICATES)

        if self.client_ctx:
            relations.add(OrganizationRelations.CLIENTS)

        return relations
