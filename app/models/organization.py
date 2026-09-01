from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.organization import OrganizationEntity
from app.db.repository.query_builder.organization_query_builder import (
    CertificateQueryContext,
    SourceQueryContext,
)
from app.models.base import (
    INCLUDE_DELETED_DESCRIPTION,
    CommonModel,
    sanatize_model_scopes,
)
from app.models.certificates import Certificate, CertificateCreate, CertificateUpdate
from app.models.client import Client, ClientCreate
from app.models.source import Source, SourceCreate, SourceUpdate
from app.models.ura import UraNumber

EXTERNAL_ID_DESCRIPTION = "The identifier of the organization 'OIN' or 'URA'"
NAME_DESCRIPTION = "The name of the organization"
SCOPES_DESCRIPTION = "The space separated scopes granted to the organization"


class OrganizationFields(BaseModel):
    external_id: UraNumber = Field(..., description=EXTERNAL_ID_DESCRIPTION)
    name: str = Field(..., description=NAME_DESCRIPTION)
    scopes: str | None = Field(default=None, description=SCOPES_DESCRIPTION)


class OrganizationCreate(OrganizationFields):
    external_id: UraNumber = Field(..., description=EXTERNAL_ID_DESCRIPTION)
    name: str = Field(..., description=NAME_DESCRIPTION)
    certificates: list[CertificateCreate] | None = Field(default=None)
    sources: list[SourceCreate] | None = Field(default=None)
    clients: list[ClientCreate] | None = Field(default=None)

    @property
    def sanitized_scopes(self) -> list[str] | None:
        return sanatize_model_scopes(self.scopes)

    @property
    def source_ids(self) -> list[str]:
        if self.sources is None:
            raise AttributeError("source_ids cannot be accessed if sources is of value None")

        return [s.source_id for s in self.sources]

    @property
    def client_certs(self) -> list[CertificateCreate]:
        if self.clients is None:
            return []

        results = []
        for client in self.clients:
            if client.certificates is None:
                continue

            for cert in client.certificates:
                results.append(cert)

        return results


class OrganizationUpdate(BaseModel):
    name: str = Field(..., description=NAME_DESCRIPTION)
    scopes: str | None = Field(default=None, description=SCOPES_DESCRIPTION)
    certificates: list[CertificateUpdate] | None = None
    sources: list[SourceUpdate] | None = None

    @property
    def sanitized_scopes(self) -> list[str] | None:
        return sanatize_model_scopes(self.scopes)

    @classmethod
    def from_entity(cls, entity: OrganizationEntity, include_deleted: bool = False) -> Self:
        certs: list[CertificateUpdate] | None = None
        sources: list[SourceUpdate] | None = None
        scopes = [s.name for s in entity.scopes]
        if include_deleted:
            certs = [CertificateUpdate.from_entity(c) for c in entity.certificates] if entity.certificates else None
            sources = [SourceUpdate.from_entity(s) for s in entity.sources] if entity.sources else None
        else:
            certs = (
                [CertificateUpdate.from_entity(c) for c in entity.certificates if c.deleted_at is None]
                if entity.certificates
                else None
            )
            sources = (
                [SourceUpdate.from_entity(s) for s in entity.sources if s.deleted_at is None]
                if entity.sources
                else None
            )

        return cls(
            name=entity.name,
            scopes=" ".join(scopes) if scopes else None,
            certificates=certs,
            sources=sources,
        )


class OrganizationQueryParams(BaseModel):
    name: str | None = Field(default=None, description=NAME_DESCRIPTION)
    scopes: str | None = Field(default=None, description=SCOPES_DESCRIPTION)
    external_id: UraNumber | None = Field(default=None, description=EXTERNAL_ID_DESCRIPTION)
    cert_id: UUID | None = None
    cert_identifier: str | None = None  # TODO: Add description
    cert_domain: str | None = None  # TODO: Add description
    source_id: UUID | None = None
    source_name: str | None = None

    include_deleted: bool = Field(default=False, description=INCLUDE_DELETED_DESCRIPTION)

    @property
    def sanitized_scopes(self) -> list[str] | None:
        return sanatize_model_scopes(self.scopes)

    def into_cert_query_context(self) -> CertificateQueryContext:
        return CertificateQueryContext(
            id=self.cert_id, organization_identifier=self.cert_identifier, domain=self.cert_domain
        )

    def into_source_query_context(self) -> SourceQueryContext:
        return SourceQueryContext(id=self.source_id, name=self.source_name)


class Organization(CommonModel, OrganizationFields):
    model_config = ConfigDict(from_attributes=True)

    certificates: list[Certificate] | None = Field(default=None)
    sources: list[Source] | None = Field(default=None)
    clients: list[Client] | None = Field(default=None)

    @classmethod
    def from_entity(cls, entity: OrganizationEntity) -> Self:
        scopes = " ".join([s.name for s in entity.scopes]) if entity.scopes else None
        return cls(
            id=entity.id,
            external_id=entity.external_id,
            name=entity.name,
            scopes=scopes,
            clients=[Client.from_entity(c) for c in entity.clients] if entity.clients else None,
            certificates=[Certificate.from_entity(c) for c in entity.certificates] if entity.certificates else None,
            sources=[Source.from_entity(s) for s in entity.sources] if entity.sources else None,
            created_at=entity.created_at,
        )
