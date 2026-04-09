import pytest

from app.models.oin_number import OinNumber


def test_create_should_succeeed() -> None:
    target = "00000121234567890001"
    actual = OinNumber(target)

    assert isinstance(actual, OinNumber)
    assert actual.value == target
    assert str(actual) == target


def test_equality_should_succeed(oin: OinNumber) -> None:
    expected = oin
    data = oin.value
    actual = OinNumber(data)

    assert expected == actual


def test_create_should_fail_with_wrong_number() -> None:
    with pytest.raises(ValueError) as exec:
        OinNumber("12345")

    assert "OIN must be 20 digits" in str(exec.value)
