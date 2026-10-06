from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.client import ClientEntity
from app.models.base import (
    INCLUDE_DELETED_DESCRIPTION,
    CommonModel,
)
from app.models.certificates import Certificate, CertificateCreate, CertificateUpdate
from app.models.oin import Oin
from app.models.scopes import AuthorizationScope
from app.models.source import Source, SourceCreate, SourceUpdate
from app.models.ura import UraNumber

ORG_URA_DESCRIPTION = "The URA (external_id) of the organization the client acts on behalf of"
DOMAIN_DESCRIPTION = "The domains from the client certificate's CN and SAN entries"
ORGANIZATION_IDENTIFIER_DESCRIPTION = "The organization_identifier of the client certificate"
MATCHED_DOMAIN_DESCRIPTION = "The registered domain that matched one of the presented certificate_domains"
EXTERNAL_ID_DESCRIPTION = "The OIN of the client"
SOURCE_ID_DESCRIPTION = "The optional source ID of the client"
SCOPES_DESCRIPTION = "The space separated scopes granted to the client"
ORGANIZATION_NAME_DESCRIPTION = "The name of the organization the client acts on behalf of"
RESOLVE_SCOPES_DESCRIPTION = (
    f"{SCOPES_DESCRIPTION}. One or more of: {', '.join(scope.value for scope in AuthorizationScope)}"
)


class ClientResolveRequest(BaseModel):
    client_id: UUID
    organization_external_id: UraNumber = Field(..., description=ORG_URA_DESCRIPTION)
    certificate_organization_identifier: Oin = Field(..., description=ORGANIZATION_IDENTIFIER_DESCRIPTION)
    certificate_domains: list[str] = Field(..., description=DOMAIN_DESCRIPTION)
    source_id: str | None = Field(default=None, description=SOURCE_ID_DESCRIPTION)


class ClientResolveResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scopes: str = Field(description=RESOLVE_SCOPES_DESCRIPTION)
    organization_name: str = Field(description=ORGANIZATION_NAME_DESCRIPTION)
    matched_domain: str = Field(description=MATCHED_DOMAIN_DESCRIPTION)


class ClientFields(BaseModel):
    name: str
    description: str | None = Field(default=None)
    scopes: list[AuthorizationScope] | None = Field(default=None, description=SCOPES_DESCRIPTION)


class ClientCreate(ClientFields):
    certificates: list[CertificateCreate] | None = None
    sources: list[SourceCreate] | None = None


class ClientOptionalFields(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str | None = None
    scopes: list[AuthorizationScope] | None = Field(default=None, description=SCOPES_DESCRIPTION)


class ClientUpdate(ClientFields):
    id: UUID
    certificates: list[CertificateUpdate] | None = None
    sources: list[SourceUpdate] | None = None


class ClientQueryParams(ClientOptionalFields):
    model_config = ConfigDict(extra="forbid")
    cert_organization_identifier: Oin | None = None
    cert_domain: str | None = None
    source_id: str | None = None
    source_name: str | None = None
    include_deleted: bool = Field(default=False, description=INCLUDE_DELETED_DESCRIPTION)


class Client(CommonModel, ClientFields):
    model_config = ConfigDict(from_attributes=True)
    organization_id: UUID
    certificates: list[Certificate] | None = None
    sources: list[Source] | None = None

    @classmethod
    def from_entity(cls, entity: ClientEntity) -> Self:
        return cls(
            id=entity.id,
            name=entity.name,
            description=entity.description,
            organization_id=entity.organization_id,
            scopes=[s.name for s in entity.scopes] if entity.scopes else None,
            certificates=[Certificate.from_entity(c) for c in entity.certificates] if entity.certificates else None,
            sources=[Source.from_entity(s) for s in entity.sources] if entity.sources else None,
            created_at=entity.created_at,
            modified_at=entity.modified_at,
            deleted_at=entity.deleted_at,
        )
