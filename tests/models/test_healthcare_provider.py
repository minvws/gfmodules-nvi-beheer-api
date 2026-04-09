from typing import Any, Dict

import pytest
from pydantic import ValidationError

from app.models.healthcare_provider import HealthcareProviderCreate, Status
from app.models.oin_number import OinNumber
from app.models.ura_number import UraNumber


def test_create_should_succeeed(oin: OinNumber, ura_number: UraNumber) -> None:
    data: Dict[str, Any] = {
        "ura_number": ura_number.value,
        "source_id": "src-1",
        "is_source": True,
        "is_viewer": False,
        "oin": oin.value,
        "common_name": "Test Provider",
        "status": "active",
    }

    model = HealthcareProviderCreate(**data)

    assert model.ura_number == data["ura_number"]
    assert model.status == Status.ACTIVE


def test_create_should_raise_exception_with_invalid_status(oin: OinNumber, ura_number: UraNumber) -> None:
    data: Dict[str, Any] = {
        "ura_number": ura_number.value,
        "source_id": "src-1",
        "is_source": True,
        "is_viewer": False,
        "oin": oin.value,
        "common_name": "Test Provider",
        "status": "invalid-status",
    }

    with pytest.raises(ValidationError):
        HealthcareProviderCreate(**data)


def test_create_should_raise_exception_invalid_ura_number(oin: OinNumber) -> None:
    data: Dict[str, Any] = {
        "ura_number": "invalid",
        "source_id": "src-1",
        "is_source": True,
        "is_viewer": False,
        "oin": oin.value,
        "common_name": "Test Provider",
        "status": "active",
    }

    with pytest.raises(ValidationError) as exc:
        HealthcareProviderCreate(**data)

    assert "Invalid UraNumber" in str(exc.value)


def test_create_should_raise_exception_invalid_oin(ura_number: UraNumber) -> None:

    data: Dict[str, Any] = {
        "ura_number": ura_number.value,
        "source_id": "src-1",
        "is_source": True,
        "is_viewer": False,
        "oin": "123467",
        "common_name": "Test Provider",
        "status": "active",
    }
    with pytest.raises(ValidationError) as exec:
        HealthcareProviderCreate(**data)

    assert "Invalid OIN" in str(exec.value)
