from typing import TypeVar


def parse(value: str | None) -> set[str]:
    if not value:
        return set()
    return set(value.split())


T = TypeVar("T")


def is_subset(parent: list[T] | None, child: list[T] | None) -> bool:
    child_set = set(child) if child else set()
    parent_set = set(parent) if parent else set()
    return child_set.issubset(parent_set)
