from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.client import ClientEntity
from app.models.base import (
    INCLUDE_DELETED_DESCRIPTION,
    CommonModel,
    sanatize_model_scopes,
)
from app.models.certificates import Certificate, CertificateCreate
from app.models.oin import Oin
from app.models.ura import UraNumber

ORG_URA_DESCRIPTION = "The URA (register_id) of the organization the client acts on behalf of"
COMMON_NAME_DESCRIPTION = "The certificate CN of the client"
EXTERNAL_ID_DESCRIPTION = "The OIN of the client"
SOURCE_ID_DESCRIPTION = "The optional source ID of the client"
SCOPES_DESCRIPTION = "The space separated scopes granted to the client"
ORGANIZATION_NAME_DESCRIPTION = "The name of the organization the client acts on behalf of"


class ClientResolveRequest(BaseModel):
    client_organization_id: Oin = Field(..., description=EXTERNAL_ID_DESCRIPTION)
    client_common_name: str = Field(..., description=COMMON_NAME_DESCRIPTION)
    organization_id: UraNumber = Field(..., description=ORG_URA_DESCRIPTION)


class ClientResolveResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    scopes: str | None = Field(default=None, description=SCOPES_DESCRIPTION)
    source_id: str | None = Field(default=None, description=SOURCE_ID_DESCRIPTION)
    organization_name: str | None = Field(default=None, description=ORGANIZATION_NAME_DESCRIPTION)


class ClientFields(BaseModel):
    name: str
    description: str | None = Field(default=None)
    scopes: str | None = Field(default=None, description=SCOPES_DESCRIPTION)


class ClientCreate(ClientFields):
    name: str
    description: str | None = Field(default=None)
    scopes: str | None = Field(default=None, description=SCOPES_DESCRIPTION)
    certificates: list[CertificateCreate] | None = None

    @property
    def sanatized_scopes(self) -> list[str] | None:
        return sanatize_model_scopes(self.scopes)


class ClientOptionalFields(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    external_id: Oin | None = Field(default=None, description=EXTERNAL_ID_DESCRIPTION)
    scopes: str | None = Field(default=None, description=SCOPES_DESCRIPTION)


class ClientUpdate(ClientCreate):
    @property
    def sanatized_scopes(self) -> list[str] | None:
        return sanatize_model_scopes(self.scopes)


class ClientQueryParams(ClientOptionalFields):
    include_deleted: bool = Field(default=False, description=INCLUDE_DELETED_DESCRIPTION)

    @property
    def sanatized_scope(self) -> list[str] | None:
        return sanatize_model_scopes(self.scopes)


class Client(CommonModel, ClientFields):
    model_config = ConfigDict(from_attributes=True)
    organization_id: UUID
    certificates: list[Certificate] | None = None

    @classmethod
    def from_entity(cls, entity: ClientEntity) -> Self:
        return cls(
            id=entity.id,
            name=entity.name,
            description=entity.description,
            organization_id=entity.organization_id,
            scopes=" ".join(entity.client_scopes) if entity.client_scopes else None,
            certificates=[Certificate.from_entity(c) for c in entity.certificates] if entity.certificates else None,
            created_at=entity.created_at,
        )
