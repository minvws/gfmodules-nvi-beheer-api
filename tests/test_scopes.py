from app import utils


def test_parse_splits_on_whitespace() -> None:
    assert utils.parse("read write") == {"read", "write"}


def test_parse_collapses_extra_whitespace() -> None:
    assert utils.parse("  read   write\twrite ") == {"read", "write"}


def test_parse_none_is_empty() -> None:
    assert utils.parse(None) == set()


def test_parse_empty_string_is_empty() -> None:
    assert utils.parse("") == set()


def test_is_subset_true() -> None:
    assert utils.is_subset(["read"], ["read write"]) is True


def test_is_subset_equal() -> None:
    assert utils.is_subset(["read write"], ["write read"]) is True


def test_is_subset_empty_child_is_always_subset() -> None:
    assert utils.is_subset([""], ["read"]) is True
    assert utils.is_subset(None, None) is True


def test_is_subset_false() -> None:
    assert utils.is_subset(["read delete"], ["read write"]) is False
