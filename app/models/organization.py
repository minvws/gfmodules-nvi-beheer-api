from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.db.models.organization import OrganizationEntity
from app.db.repository.contexts.organization_context import (
    OrganizationCertificateQueryContext,
    OrganizationClientQueryContext,
    OrganizationQueryContext,
    OrganizationSourceQueryContext,
)
from app.models.base import (
    INCLUDE_DELETED_DESCRIPTION,
    CommonModel,
)
from app.models.certificates import Certificate, CertificateCreate
from app.models.client import Client, ClientCreate
from app.models.oin import Oin
from app.models.scopes import AuthorizationScope
from app.models.source import Source, SourceCreate
from app.models.ura import UraNumber

EXTERNAL_ID_DESCRIPTION = "The identifier of the organization 'OIN' or 'URA'"
NAME_DESCRIPTION = "The name of the organization"
SCOPES_DESCRIPTION = "list of scopes granted to the organization"


class OrganizationFields(BaseModel):
    external_id: UraNumber = Field(..., description=EXTERNAL_ID_DESCRIPTION)
    name: str = Field(..., description=NAME_DESCRIPTION)
    scopes: list[AuthorizationScope] | None = Field(
        default=None, description=SCOPES_DESCRIPTION, examples=[[AuthorizationScope.READ]]
    )

    @field_serializer("external_id")
    def serialize_external_id(self, external_id: UraNumber) -> str:
        return self.external_id.value


class OrganizationCreate(OrganizationFields):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    external_id: UraNumber = Field(..., description=EXTERNAL_ID_DESCRIPTION)
    name: str = Field(..., description=NAME_DESCRIPTION)
    certificates: list[CertificateCreate] | None = Field(default=None)
    sources: list[SourceCreate] | None = Field(default=None)
    clients: list[ClientCreate] | None = Field(default=None)

    @property
    def source_ids(self) -> list[str]:
        if self.sources is None:
            raise AttributeError("source_ids cannot be accessed if sources is of value None")

        return [s.source_id for s in self.sources]


class OrganizationUpdate(BaseModel):
    external_id: UraNumber = Field(..., description=EXTERNAL_ID_DESCRIPTION)
    name: str = Field(..., description=NAME_DESCRIPTION)
    scopes: list[AuthorizationScope] | None = Field(default=None, description=SCOPES_DESCRIPTION)

    @classmethod
    def from_entity(cls, entity: OrganizationEntity, include_deleted: bool = False) -> Self:
        return cls(
            name=entity.name,
            external_id=entity.external_id,
            scopes=[s.name for s in entity.scopes] if entity.scopes else None,
        )


class OrganizationQueryParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, description=NAME_DESCRIPTION)
    scopes: list[AuthorizationScope] | None = Field(default=None, description=SCOPES_DESCRIPTION)
    external_id: UraNumber | None = Field(default=None, description=EXTERNAL_ID_DESCRIPTION)
    cert_id: UUID | None = None
    cert_identifier: Oin | None = None
    cert_domain: str | None = None
    source_id: str | None = None
    source_name: str | None = None
    client_name: str | None = None
    client_scopes: list[AuthorizationScope] | None = None
    client_cert_identifier: Oin | None = None
    client_cert_domain: str | None = None
    client_source_id: str | None = None
    client_source_name: str | None = None

    include_deleted: bool = Field(default=False, description=INCLUDE_DELETED_DESCRIPTION)

    def into_org_client_query_context(self) -> OrganizationClientQueryContext:
        return OrganizationClientQueryContext(
            name=self.client_name,
            scopes=self.client_scopes,
            certificate_ctx=OrganizationCertificateQueryContext(
                organization_identifier=self.client_cert_identifier, domain=self.client_cert_domain
            ),
            source_ctx=OrganizationSourceQueryContext(source_id=self.client_source_id, name=self.client_source_name),
        )

    def into_cert_query_context(self) -> OrganizationCertificateQueryContext:
        return OrganizationCertificateQueryContext(
            id=self.cert_id, organization_identifier=self.cert_identifier, domain=self.cert_domain
        )

    def into_source_query_context(self) -> OrganizationSourceQueryContext:
        return OrganizationSourceQueryContext(source_id=self.source_id, name=self.source_name)

    def into_organization_query_context(self) -> OrganizationQueryContext:
        src_ctx = self.into_source_query_context()
        crt_ctx = self.into_cert_query_context()
        client_ctx = self.into_org_client_query_context()
        return OrganizationQueryContext(
            external_id=self.external_id,
            name=self.name,
            scopes=self.scopes,
            client_ctx=client_ctx,
            source_ctx=src_ctx,
            certificate_ctx=crt_ctx,
        )


class Organization(CommonModel, OrganizationFields):
    model_config = ConfigDict(from_attributes=True)

    certificates: list[Certificate] | None = Field(default=None)
    sources: list[Source] | None = Field(default=None)
    clients: list[Client] | None = Field(default=None)

    @classmethod
    def from_entity(cls, entity: OrganizationEntity) -> Self:
        return cls(
            id=entity.id,
            external_id=entity.external_id,
            name=entity.name,
            scopes=[s.name for s in entity.scopes] if entity else None,
            clients=[Client.from_entity(c) for c in entity.clients] if entity.clients else None,
            certificates=[Certificate.from_entity(c) for c in entity.certificates] if entity.certificates else None,
            sources=[Source.from_entity(s) for s in entity.sources] if entity.sources else None,
            created_at=entity.created_at,
            modified_at=entity.modified_at,
            deleted_at=entity.deleted_at,
        )
