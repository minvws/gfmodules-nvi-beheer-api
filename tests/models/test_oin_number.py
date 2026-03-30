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


def test_create_should_fail_with_non_integer_or_str() -> None:
    with pytest.raises(ValueError) as exec:
        OinNumber({"message": "hello world"})

    assert "OIN number must be a string or integer" in str(exec.value)


def test_create_should_fail_when_passing_a_negative_number() -> None:
    with pytest.raises(ValueError) as exec:
        OinNumber(-1234)

    assert "OIN number must be a positive integer" in str(exec.value)


def test_create_should_fail_with_number_less_than_20() -> None:
    with pytest.raises(ValueError) as exec:
        OinNumber("12345")

    assert "OIN number must be exactly 20 digits" in str(exec.value)


def test_create_should_fail_when_passing_non_digits() -> None:
    with pytest.raises(ValueError) as exec:
        OinNumber("abc123")

    assert "OIN number must contain digits only" in str(exec.value)
