"""
Building blocks for the soft-delete aware queries in the repositories.

Every relationship query has the same shape: optionally hide soft-deleted rows, then either narrow which
related rows get loaded (``narrowed``) or require that a matching related row exists (``any_matching``).
"""

from typing import Any, Protocol, cast

from sqlalchemy import ColumnElement, and_
from sqlalchemy.orm import QueryableAttribute

from app.db.models.base import CommonColumns

type Conditions = list[ColumnElement[bool]]


class HasConditions(Protocol):
    def get_conditions(self) -> list[Any]: ...


def conditions_of(ctx: HasConditions | None) -> Conditions:
    return ctx.get_conditions() if ctx else []


def not_deleted(entity: type[CommonColumns], include_deleted: bool) -> Conditions:
    """The condition that hides soft-deleted rows of `entity`, or none when deleted rows are wanted."""
    return [] if include_deleted else [entity.deleted_at.is_(None)]


def narrowed[T](relationship: QueryableAttribute[T], conditions: Conditions) -> QueryableAttribute[T]:
    """The relationship limited to related rows matching `conditions`, for use in a loader option."""
    if not conditions:
        return relationship
    # and_() returns the same relationship with extra criteria; SQLAlchemy's stubs type it QueryableAttribute[bool].
    return cast(QueryableAttribute[T], relationship.and_(*conditions))


def any_matching[E: CommonColumns](
    relationship: QueryableAttribute[list[E]],
    conditions: Conditions,
    entity: type[E],
    include_deleted: bool,
) -> Conditions:
    """
    A condition requiring a related row that matches `conditions` (and is not soft-deleted, unless
    `include_deleted`). No condition at all when `conditions` is empty, so an unused filter matches everything.
    """
    if not conditions:
        return []
    return [relationship.any(and_(*conditions, *not_deleted(entity, include_deleted)))]
