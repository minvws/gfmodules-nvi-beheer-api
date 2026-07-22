from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.container import get_allowed_scopes
from app.models.base import INCLUDE_DELETED_DESCRIPTION, CommonModel
from app.models.ura import UraNumber
from app.scope_utils import check_in_configured_scopes

REGISTER_ID_DESCRIPTION = "The identifier of the organization 'OIN' or 'URA'"
NAME_DESCRIPTION = "The name of the organization"
SCOPES_DESCRIPTION = "The space separated scopes granted to the organization"


class Scopes(BaseModel):
    """The scopes field as stored. Deliberately unvalidated so that responses can always be
    rendered, even for records holding a scope the configured allow-list no longer contains."""

    scopes: str | None = Field(default=None, description=SCOPES_DESCRIPTION)


class ValidatedScopes(Scopes):
    """The scopes field as accepted on request bodies: restricted to the configured allow-list."""

    @field_validator("scopes", mode="before")
    @classmethod
    def is_allowed(cls, value: str | None) -> str | None:
        allowed_scopes = get_allowed_scopes()
        if not check_in_configured_scopes(allowed_scopes, value):
            supported = " ".join(sorted(allowed_scopes))
            raise ValueError(f"Requested scopes {value} are not allowed. Supported scopes are {supported}")
        return value


class OrganizationFields(Scopes):
    register_id: UraNumber = Field(..., description=REGISTER_ID_DESCRIPTION)
    name: str = Field(..., description=NAME_DESCRIPTION)


class OrganizationCreate(ValidatedScopes, OrganizationFields):
    pass


class OrganizationUpdate(ValidatedScopes):
    name: str | None = Field(default=None, description=NAME_DESCRIPTION)


class OrganizationQueryParams(BaseModel):
    register_id: UraNumber | None = Field(default=None, description=REGISTER_ID_DESCRIPTION)
    name: str | None = Field(default=None, description=NAME_DESCRIPTION)
    scopes: str | None = Field(default=None, description=SCOPES_DESCRIPTION)
    include_deleted: bool = Field(default=False, description=INCLUDE_DELETED_DESCRIPTION)


class Organization(CommonModel, OrganizationFields):
    model_config = ConfigDict(from_attributes=True)
