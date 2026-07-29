from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

INCLUDE_DELETED_DESCRIPTION = "Include soft-deleted clients in the results"


class CommonModel(BaseModel):
    id: UUID
    created_at: datetime
    deleted_at: datetime | None = None


def sanatize_model_scopes(scopes: str | None) -> list[str] | None:
    if scopes is None:
        return None

    stripped_scopes = scopes.lstrip().rstrip()
    return [x.strip() for x in stripped_scopes.split(" ")]
