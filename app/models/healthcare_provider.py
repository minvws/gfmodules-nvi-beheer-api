from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.ura_number import UraNumber


class Status(str, Enum):
    ACTIVE = "active"
    SOFT_FREEZE = "soft-freeze"
    SUSPENDED = "suspended"
    HARD_BLOCKED = "hard-blocked"


class HealthcareProviderCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ura_number: str
    source_id: str
    is_source: bool
    is_viewer: bool
    oin: str
    common_name: str
    status: Status

    @field_validator("ura_number")
    @classmethod
    def validate_ura_number(cls, value: Any) -> str:
        try:
            result = UraNumber(value)
        except ValueError as e:
            raise ValueError(f"Invalid UraNumber: {e}")

        return result.value


class HealthcareProviderUpdate(HealthcareProviderCreate):
    pass


class HealthcareProvider(HealthcareProviderCreate):
    id: UUID
    deleted_at: datetime | None = None
