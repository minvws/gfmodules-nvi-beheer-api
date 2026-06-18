from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.base import INCLUDE_DELETED_DESCRIPTION, CommonModel
from app.models.oin import Oin
from app.models.ura import UraNumber

ORG_URA_DESCRIPTION = "The URA (register_id) of the organization the client acts on behalf of"
COMMON_NAME_DESCRIPTION = "The certificate CN of the client"
OIN_DESCRIPTION = "The OIN of the client"
SOURCE_ID_DESCRIPTION = "The optional source ID of the client"
SCOPES_DESCRIPTION = "The space separated scopes granted to the client"


class ClientResolveRequest(BaseModel):
    oin: Oin = Field(..., description=OIN_DESCRIPTION)
    common_name: str = Field(..., description=COMMON_NAME_DESCRIPTION)
    org_ura: UraNumber = Field(..., description=ORG_URA_DESCRIPTION)


class ClientResolveResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    scopes: str | None = Field(default=None, description=SCOPES_DESCRIPTION)
    source_id: str | None = Field(default=None, description=SOURCE_ID_DESCRIPTION)


class ClientCreate(BaseModel):
    oin: Oin = Field(..., description=OIN_DESCRIPTION)
    common_name: str = Field(..., description=COMMON_NAME_DESCRIPTION)
    source_id: str | None = Field(default=None, description=SOURCE_ID_DESCRIPTION)
    scopes: str | None = Field(default=None, description=SCOPES_DESCRIPTION)


class ClientOptionalFields(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    oin: Oin | None = Field(default=None, description=OIN_DESCRIPTION)
    common_name: str | None = Field(default=None, description=COMMON_NAME_DESCRIPTION)
    source_id: str | None = Field(default=None, description=SOURCE_ID_DESCRIPTION)
    scopes: str | None = Field(default=None, description=SCOPES_DESCRIPTION)


class ClientUpdate(ClientOptionalFields):
    pass


class ClientQueryParams(ClientOptionalFields):
    include_deleted: bool = Field(default=False, description=INCLUDE_DELETED_DESCRIPTION)


class Client(CommonModel, ClientCreate):
    model_config = ConfigDict(from_attributes=True)
    organization_id: UUID
