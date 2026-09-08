from dataclasses import dataclass
from typing import Any, Self
from uuid import UUID

from app.db.repository.query_builder.context.data import (
    CertificateQueryContextBase,
    ClientQueryContextBase,
    OrganizationQueryContextBase,
)


@dataclass()
class CertificateOrganizationQueryContext(OrganizationQueryContextBase):
    id: UUID | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "external_id": self.external_id}

    @classmethod
    def default(cls) -> Self:
        return cls()


@dataclass()
class CertificateClientQueryContext(ClientQueryContextBase):
    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "description": self.description}

    @classmethod
    def default(cls) -> Self:
        return cls()


@dataclass()
class CertificateQueryContext(CertificateQueryContextBase):
    organization_id: UUID | None = None
    organization_ctx: CertificateOrganizationQueryContext | None = None
    client_ctx: CertificateClientQueryContext | None = None
