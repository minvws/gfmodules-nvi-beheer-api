from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Self

from app.db.repository.query_builder.context.data import (
    CertificateQueryContextBase,
    ClientQueryContextBase,
    SourceQueryContextBase,
)


class ClientRelations(Enum):
    SCOPES = auto()
    CERTIFICATES = auto()
    SOURCES = auto()


@dataclass()
class ClientCertificateQueryContext(CertificateQueryContextBase):
    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "organization_identifier": self.organization_identifier, "domain": self.domain}


@dataclass()
class ClientSourceQueryContext(SourceQueryContextBase):
    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "source_id": self.source_id, "name": self.name}


@dataclass()
class ClientQueryContext(ClientQueryContextBase):
    scopes: list[str] | None = None
    certificate_ctx: ClientCertificateQueryContext | None = None
    source_ctx: ClientSourceQueryContext | None = None

    @classmethod
    def default(cls) -> Self:
        cert_ctx = ClientCertificateQueryContext.default()
        src_ctx = ClientSourceQueryContext.default()
        return cls(
            certificate_ctx=cert_ctx,
            source_ctx=src_ctx,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "scopes": self.scopes,
            "cert_ctx": self.certificate_ctx.to_dict() if self.certificate_ctx else None,
            "source_ctx": self.source_ctx.to_dict() if self.source_ctx else None,
        }

    @property
    def include(self) -> set[ClientRelations]:
        relations = {ClientRelations.SCOPES}
        if self.source_ctx:
            relations.add(ClientRelations.SOURCES)

        if self.certificate_ctx:
            relations.add(ClientRelations.CERTIFICATES)

        return relations
