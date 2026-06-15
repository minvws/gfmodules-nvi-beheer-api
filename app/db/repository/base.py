from typing import TypeVar

from sqlalchemy import ColumnElement, literal
from sqlalchemy.orm import Mapped

from app.db import session


def scopes_contains_conditions(column: Mapped[str | None], requested: str | None) -> list[ColumnElement[bool]]:
    """Build conditions matching rows whose space-delimited scope column contains every requested scope.

    Each requested scope must appear as a whole token (so "read" does not match "readonly"). A row
    matches only when all requested scopes are present; a NULL scope column matches nothing.
    """
    if not requested:
        return []
    padded = literal(" ").concat(column).concat(literal(" "))
    return [padded.like(f"% {token} %") for token in requested.split()]


class RepositoryBase:
    """
    abstract base class for repository: not yet implemented
    """

    def __init__(self, db_session: session.DbSession):
        self.db_session = db_session


TRepositoryBase = TypeVar("TRepositoryBase", bound=RepositoryBase, covariant=True)
