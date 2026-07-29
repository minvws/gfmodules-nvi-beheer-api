from typing import Self

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.organization import OrganizationEntity
from app.models.base import (
    INCLUDE_DELETED_DESCRIPTION,
    CommonModel,
    sanatize_model_scopes,
)
from app.models.ura import UraNumber

REGISTER_ID_DESCRIPTION = "The identifier of the organization 'OIN' or 'URA'"
NAME_DESCRIPTION = "The name of the organization"
SCOPES_DESCRIPTION = "The space separated scopes granted to the organization"


class OrganizationFields(BaseModel):
    register_id: UraNumber = Field(..., description=REGISTER_ID_DESCRIPTION)
    name: str = Field(..., description=NAME_DESCRIPTION)
    scopes: str | None = Field(..., description=SCOPES_DESCRIPTION)


class OrganizationCreate(OrganizationFields):
    register_id: UraNumber = Field(..., description=REGISTER_ID_DESCRIPTION)
    name: str = Field(..., description=NAME_DESCRIPTION)

    @property
    def sanitized_scopes(self) -> list[str] | None:
        return sanatize_model_scopes(self.scopes)


class OrganizationUpdate(BaseModel):
    name: str = Field(..., description=NAME_DESCRIPTION)
    scopes: str | None = Field(default=None, description=SCOPES_DESCRIPTION)

    @property
    def sanitized_scopes(self) -> list[str] | None:
        return sanatize_model_scopes(self.scopes)


class OrganizationQueryParams(BaseModel):
    name: str | None = Field(default=None, description=NAME_DESCRIPTION)
    scopes: str | None = Field(default=None, description=SCOPES_DESCRIPTION)
    register_id: UraNumber | None = Field(default=None, description=REGISTER_ID_DESCRIPTION)
    include_deleted: bool = Field(default=False, description=INCLUDE_DELETED_DESCRIPTION)

    @property
    def sanitized_scopes(self) -> list[str] | None:
        return sanatize_model_scopes(self.scopes)


class Organization(CommonModel, OrganizationFields):
    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_entity(cls, entity: OrganizationEntity) -> Self:
        return cls(
            id=entity.id,
            register_id=entity.register_id,
            name=entity.name,
            scopes=" ".join(entity.org_scopes) if entity.org_scopes else None,
            created_at=entity.created_at,
        )
