from pydantic import BaseModel, ConfigDict, Field

from app.models.base import INCLUDE_DELETED_DESCRIPTION, CommonModel

REGISTER_ID_DESCRIPTION = "The identifier of the organization 'OIN' or 'URA'"
NAME_DESCRIPTION = "The name of the organization"
SCOPES_DESCRIPTION = "The space separated scopes granted to the organization"


class OrganizationCreate(BaseModel):
    register_id: str = Field(..., description=REGISTER_ID_DESCRIPTION)
    name: str = Field(..., description=NAME_DESCRIPTION)
    scopes: str | None = Field(default=None, description=SCOPES_DESCRIPTION)


class OrganizationUpdate(BaseModel):
    name: str | None = Field(default=None, description=NAME_DESCRIPTION)
    scopes: str | None = Field(default=None, description=SCOPES_DESCRIPTION)


class OrganizationQueryParams(OrganizationUpdate):
    register_id: str | None = Field(default=None, description=REGISTER_ID_DESCRIPTION)
    include_deleted: bool = Field(default=False, description=INCLUDE_DELETED_DESCRIPTION)


class Organization(CommonModel, OrganizationCreate):
    model_config = ConfigDict(from_attributes=True)
