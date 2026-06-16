from typing import Any

import pytest

from app.models.oin import Oin


def test_valid_string_splits_prefix_and_number() -> None:
    oin = Oin("00000001000000001000")
    assert oin.prefix == "00000001"
    assert oin.number == "000000001000"


def test_value_returns_full_20_digit_string() -> None:
    oin = Oin("00000009111122220000")
    assert oin.value == "00000009111122220000"
    assert len(oin.value) == 20


def test_str_returns_full_value() -> None:
    oin = Oin("00000001000000001000")
    assert str(oin) == "00000001000000001000"


def test_repr_format() -> None:
    oin = Oin("00000001000000001000")
    assert repr(oin) == "Oin(00000001, 000000001000)"


def test_equality_same_value() -> None:
    oin_1 = Oin("00000001000000001000")
    oin_2 = Oin("00000001000000001000")
    assert oin_1 == oin_2


def test_inequality_different_value() -> None:
    oin_1 = Oin("00000001000000001000")
    oin_2 = Oin("00000002000000002000")
    assert oin_1 != oin_2


def test_equality_with_non_instance() -> None:
    oin = Oin("00000001000000001000")
    assert oin != "00000001000000001000"


def test_hashable_usable_as_dict_key() -> None:
    oin = Oin("00000001000000001000")
    d = {oin: "value"}
    assert d[Oin("00000001000000001000")] == "value"


@pytest.mark.parametrize(
    "invalid",
    [
        "0000000100000000001",  # 19 chars — too short
        "000000010000000000001",  # 21 chars — too long
        "0000000100000000000a",  # 'a' lands in the suffix, which must be zeros
        "abcdefghijklmnopqrst",  # prefix is not digits
        "",  # empty
        None,
        12.34,
        [],
    ],
)
def test_invalid_values_raise_value_error(invalid: Any) -> None:
    with pytest.raises((ValueError, TypeError)):
        Oin(invalid)


def test_negative_int_raises_value_error() -> None:
    with pytest.raises(ValueError):
        Oin(-1)


def test_prefix_length_is_8() -> None:
    oin = Oin("12345678901234560000")
    assert len(oin.prefix) == 8


def test_number_length_is_12() -> None:
    oin = Oin("12345678901234560000")
    assert len(oin.number) == 12
