from typing import Any

from pydantic import BaseModel, field_validator

from app.models.ura_number import UraNumber


class HealthcareProvidersQueryParams(BaseModel):
    oin: str | None = None
    source_id: str | None = None
    ura_number: str | None = None

    @field_validator("ura_number")
    @classmethod
    def validate_ura_number(cls, value: Any) -> str:
        try:
            result = UraNumber(value)
        except ValueError as e:
            raise ValueError(f"Invalid UraNumber: {e}")

        return result.value
