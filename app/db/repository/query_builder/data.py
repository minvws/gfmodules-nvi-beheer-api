from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Self
from uuid import UUID

from app.models.ura import UraNumber


class LoadStrategy(Enum):
    SELECTIN_LOAD = auto()
    OUTERJOIN_LOAD = auto()


@dataclass()
class SourceQueryContext:
    id: UUID | None = None
    source_id: str | None = None
    name: str | None = None

    @classmethod
    def default(cls) -> Self:
        return cls()

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "source_id": self.source_id, "name": self.name}


@dataclass
class CertificateQueryContext:
    id: UUID | None = None
    organization_identifier: str | None = None
    domain: str | None = None

    @classmethod
    def default(cls) -> Self:
        return cls()

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "organization_identifier": self.organization_identifier, "domain": self.domain}


class ClientRelations(Enum):
    SCOPES = auto()
    CERTIFICATES = auto()
    SOURCES = auto()


@dataclass
class ClientQueryContext:
    id: UUID | None = None
    name: str | None = None
    description: str | None = None
    scopes: list[str] | None = None
    cert_ctx: CertificateQueryContext | None = None
    source_ctx: SourceQueryContext | None = None
    include_scopes: bool = True

    @classmethod
    def default(cls) -> Self:
        cert_ctx = CertificateQueryContext.default()
        src_ctx = SourceQueryContext.default()
        return cls(
            cert_ctx=cert_ctx,
            source_ctx=src_ctx,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "scopes": self.scopes,
            "cert_ctx": self.cert_ctx.to_dict() if self.cert_ctx else None,
            "source_ctx": self.source_ctx.to_dict() if self.source_ctx else None,
        }

    @property
    def include(self) -> set[ClientRelations]:
        relations = {ClientRelations.SCOPES}
        if self.source_ctx:
            relations.add(ClientRelations.SOURCES)

        if self.cert_ctx:
            relations.add(ClientRelations.CERTIFICATES)

        return relations


class OrganizationRelations(Enum):
    CLIENTS = auto()
    CERTIFICATES = auto()
    SOURCES = auto()
    SCOPES = auto()


@dataclass
class OrganizationQueryContext:
    external_id: UraNumber | None = None
    name: str | None = None
    scopes: list[str] | None = None
    client_ctx: ClientQueryContext | None = None
    source_ctx: SourceQueryContext | None = None
    certificate_ctx: CertificateQueryContext | None = None

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
