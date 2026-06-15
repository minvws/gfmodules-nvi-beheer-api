from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

INCLUDE_DELETED_DESCRIPTION = "Include soft-deleted clients in the results"


class Base(BaseModel):
    id: UUID
    created_at: datetime
    deleted_at: datetime | None = None
