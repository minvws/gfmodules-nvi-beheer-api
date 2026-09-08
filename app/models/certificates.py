from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field

from app.db.models.certificate import CertificateEntity
from app.models.base import CommonModel, CommonQueryParams
from app.models.oin import Oin


class CertificateOptionalFields(BaseModel):
    organization_identifier: Oin | None = Field(default=None)
    domain: str | None = Field(default=None)


class CertificateQueryParams(CommonQueryParams, CertificateOptionalFields):
    pass


class ClientCertificateQueryParams(CertificateOptionalFields):
    pass


class CertificateField(BaseModel):
    organization_identifier: Oin
    domain: str

    def make_unique_key(self, organization_id: UUID) -> str:
        return f"{str(organization_id)}-{str(self.organization_identifier)}-{self.domain}"


class CertificateCreate(CertificateField):
    pass


class CertificateUpdate(CertificateField):
    id: UUID

    @classmethod
    def from_entity(cls, entity: CertificateEntity) -> Self:
        return cls(id=entity.id, organization_identifier=entity.organization_identifier, domain=entity.domain)


class Certificate(CommonModel, CertificateField):
    @classmethod
    def from_entity(cls, entity: CertificateEntity) -> Self:
        return cls(
            id=entity.id,
            organization_identifier=entity.organization_identifier,
            domain=entity.domain,
            created_at=entity.created_at,
        )
