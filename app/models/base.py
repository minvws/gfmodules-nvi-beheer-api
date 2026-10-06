from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

INCLUDE_DELETED_DESCRIPTION = "Include soft-deleted clients in the results"


class CommonModel(BaseModel):
    id: UUID
    created_at: datetime
    modified_at: datetime | None = None
    deleted_at: datetime | None = None


class CommonQueryParams(BaseModel):
    include_deleted: bool = Field(default=False)
