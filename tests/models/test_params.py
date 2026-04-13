import pytest

from app.models.params import HealthcareProvidersQueryParams
from app.models.ura_number import UraNumber


def test_serialize_should_succeed(ura_number: UraNumber) -> None:
    expected = {
        "oin": "000000912345678",
        "source_id": "some-id",
        "ura_number": ura_number.value,
    }
    data = HealthcareProvidersQueryParams(oin="000000912345678", source_id="some-id", ura_number=ura_number.value)

    actual = data.model_dump()

    assert expected == actual


def test_deserialize_should_succeed(ura_number: UraNumber) -> None:
    expected = HealthcareProvidersQueryParams(oin="000000912345678", source_id="some-id", ura_number=ura_number.value)
    data = {
        "oin": "000000912345678",
        "source_id": "some-id",
        "ura_number": ura_number.value,
    }

    actual = HealthcareProvidersQueryParams.model_validate(data)

    assert expected == actual


def test_deserialize_should_raise_exception_with_invalid_ura() -> None:
    with pytest.raises(ValueError) as exc:
        HealthcareProvidersQueryParams(oin="0000123456789", source_id="some-id", ura_number="INVALID-URA")

    assert "Invalid UraNumber" in str(exc.value)
