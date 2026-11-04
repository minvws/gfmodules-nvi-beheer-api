"""
Building blocks for the soft-delete aware queries in the repositories.

Every relationship query has the same shape: optionally hide soft-deleted rows, then either narrow which
related rows get loaded (``narrowed``) or require that a matching related row exists (``any_matching``).
"""

from typing import Any, Protocol

from sqlalchemy import and_


class HasConditions(Protocol):
    def get_conditions(self) -> list[Any]: ...


def conditions_of(ctx: HasConditions | None) -> list[Any]:
    return ctx.get_conditions() if ctx else []


def not_deleted(entity: Any, include_deleted: bool) -> list[Any]:
    """The condition that hides soft-deleted rows of `entity`, or none when deleted rows are wanted."""
    return [] if include_deleted else [entity.deleted_at.is_(None)]


def narrowed(relationship: Any, conditions: list[Any]) -> Any:
    """The relationship limited to related rows matching `conditions`, for use in a loader option."""
    return relationship.and_(*conditions) if conditions else relationship


def any_matching(relationship: Any, conditions: list[Any], entity: Any, include_deleted: bool) -> list[Any]:
    """
    A condition requiring a related row that matches `conditions` (and is not soft-deleted, unless
    `include_deleted`). No condition at all when `conditions` is empty, so an unused filter matches everything.
    """
    if not conditions:
        return []
    return [relationship.any(and_(*conditions, *not_deleted(entity, include_deleted)))]
