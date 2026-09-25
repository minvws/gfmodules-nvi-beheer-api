from dataclasses import dataclass
from typing import Any, Self
from uuid import UUID

from app.db.models.certificate import CertificateEntity
from app.db.models.client import ClientEntity
from app.db.models.organization import OrganizationEntity
from app.db.repository.contexts.data import (
    CertificateQueryContextBase,
    ClientQueryContextBase,
    OrganizationQueryContextBase,
)


@dataclass()
class CertificateOrganizationQueryContext(OrganizationQueryContextBase):
    id: UUID | None = None

    @classmethod
    def default(cls) -> Self:
        return cls()

    def get_conditions(self) -> list[Any]:
        org_filters = []
        if self.id:
            org_filters.append(OrganizationEntity.id == self.id)

        if self.external_id:
            org_filters.append(OrganizationEntity.external_id == self.external_id)

        if self.name:
            org_filters.append(OrganizationEntity.name == self.name)

        return org_filters


@dataclass()
class CertificateClientQueryContext(ClientQueryContextBase):
    @classmethod
    def default(cls) -> Self:
        return cls()

    def get_conditions(self) -> list[Any]:
        client_filters = []
        if self.organization_id:
            client_filters.append(ClientEntity.organization_id == self.organization_id)

        if self.id:
            client_filters.append(ClientEntity.id == self.id)

        if self.name:
            client_filters.append(ClientEntity.name == self.name)

        if self.description:
            client_filters.append(ClientEntity.description == self.description)

        return client_filters


@dataclass()
class CertificateQueryContext(CertificateQueryContextBase):
    organization_id: UUID | None = None
    organization_ctx: CertificateOrganizationQueryContext | None = None
    client_ctx: CertificateClientQueryContext | None = None

    def get_conditions(self) -> list[Any]:
        cert_filters = []
        if self.id:
            cert_filters.append(CertificateEntity.id == self.id)

        if self.organization_id:
            cert_filters.append(CertificateEntity.organization_id == self.organization_id)

        if self.organization_identifier:
            cert_filters.append(CertificateEntity.organization_identifier == self.organization_identifier)

        if self.domain:
            cert_filters.append(CertificateEntity.domain == self.domain)

        return cert_filters
