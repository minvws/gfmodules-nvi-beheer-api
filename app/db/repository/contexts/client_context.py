from dataclasses import dataclass
from typing import Any, Self

from app.db.models.certificate import CertificateEntity
from app.db.models.client import ClientEntity
from app.db.models.source import SourceEntity
from app.db.repository.contexts.data import (
    CertificateQueryContextBase,
    ClientQueryContextBase,
    SourceQueryContextBase,
)


@dataclass()
class ClientCertificateQueryContext(CertificateQueryContextBase):
    def get_conditions(self) -> list[Any]:
        crt_conditions = []

        if self.id:
            crt_conditions.append(CertificateEntity.id == self.id)

        if self.domain:
            crt_conditions.append(CertificateEntity.domain == self.domain)

        if self.organization_identifier:
            crt_conditions.append(CertificateEntity.organization_identifier == self.organization_identifier)

        return crt_conditions


@dataclass()
class ClientSourceQueryContext(SourceQueryContextBase):
    def get_conditions(self) -> list[Any]:
        src_filters = []
        if self.id:
            src_filters.append(SourceEntity.id == self.id)
        if self.name:
            src_filters.append(SourceEntity.name == self.name)
        if self.source_id:
            src_filters.append(SourceEntity.source_id == self.source_id)

        return src_filters


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

    def get_conditions(self) -> list[Any]:
        root_filter = []
        if self.id:
            root_filter.append(ClientEntity.id == self.id)

        if self.organization_id:
            root_filter.append(ClientEntity.organization_id == self.organization_id)

        if self.name:
            root_filter.append(ClientEntity.name == self.name)

        if self.description:
            root_filter.append(ClientEntity.description == self.description)

        return root_filter
