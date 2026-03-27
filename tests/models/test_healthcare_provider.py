from typing import Any, Dict

import pytest
from pydantic import ValidationError

from app.models.healthcare_provider import HealthcareProviderCreate, Status


def test_create_should_succeeed() -> None:
    data: Dict[str, Any] = {
        "ura_number": "12345678",
        "source_id": "src-1",
        "is_source": True,
        "is_viewer": False,
        "oin": "oin-123",
        "common_name": "Test Provider",
        "status": "active",
    }

    model = HealthcareProviderCreate(**data)

    assert model.ura_number == data["ura_number"]
    assert model.status == Status.ACTIVE


def test_create_should_raise_exception_with_invalid_status() -> None:
    data: Dict[str, Any] = {
        "ura_number": "12345678",
        "source_id": "src-1",
        "is_source": True,
        "is_viewer": False,
        "oin": "oin-123",
        "common_name": "Test Provider",
        "status": "invalid-status",
    }

    with pytest.raises(ValidationError):
        HealthcareProviderCreate(**data)


def test_create_should_raise_exception_invalid_ura_number() -> None:
    data: Dict[str, Any] = {
        "ura_number": "invalid",
        "source_id": "src-1",
        "is_source": True,
        "is_viewer": False,
        "oin": "oin-123",
        "common_name": "Test Provider",
        "status": "active",
    }

    with pytest.raises(ValidationError) as exc:
        HealthcareProviderCreate(**data)

    assert "Invalid UraNumber" in str(exc.value)
