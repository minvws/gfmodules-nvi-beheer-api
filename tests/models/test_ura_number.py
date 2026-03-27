from typing import Any

import pytest

from app.models.ura_number import UraNumber


def test_with_int_should_return_str_with_exact_len() -> None:
    expected = "00000123"
    actual = UraNumber(123)
    assert actual.value == expected
    assert len(actual.value) == 8


def test_with_str_should_return_str_with_exact_len() -> None:
    expected = "00000045"
    actual = UraNumber("45")
    assert actual.value == expected
    assert len(actual.value) == 8


@pytest.mark.parametrize(
    "invalid",
    [
        "abc",
        "123456789",
        123456789,
        "12a345",
        None,
        12.34,
    ],
)
def test_invalid_values_raise_value_error(invalid: Any) -> None:
    with pytest.raises(ValueError):
        UraNumber(invalid)


def test_str_should_succeed() -> None:
    expected = "00000089"
    actual = UraNumber(89)
    assert str(actual) == expected


def test_repr_format_should_represent_properly() -> None:
    expected = "UraNumber(00001234)"
    actual = UraNumber("1234")
    assert repr(actual) == expected


def test_equality_should_succeed() -> None:
    ura_1 = UraNumber("123")
    ura_2 = UraNumber(123)
    assert ura_1 == ura_2


def test_inequality_should_succeed_with_same_instance() -> None:
    ura_1 = UraNumber(1)
    ura_2 = UraNumber(2)
    assert ura_1 != ura_2


def test_equality_with_non_instance_should_succeed() -> None:
    u = UraNumber(10)
    assert u != "00000010"
