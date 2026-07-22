from typing import List


def parse(value: str | None) -> set[str]:
    if not value:
        return set()
    return set(value.split())


def is_subset(parent: List[str] | None, child: List[str] | None) -> bool:
    child_set = set(child) if child else set()
    parent_set = set(parent) if parent else set()
    return child_set.issubset(parent_set)
