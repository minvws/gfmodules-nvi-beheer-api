from typing import Sequence

from sqlalchemy import select

from app.db.decorator import repository
from app.db.models.scope import ScopeEntity
from app.db.repository.base import RepositoryBase


@repository(ScopeEntity)
class ScopeRepository(RepositoryBase):
    def find_many(self, scopes: list[str] | None = None) -> Sequence[ScopeEntity]:
        stmt = select(ScopeEntity)
        if scopes:
            stmt = stmt.where(ScopeEntity.name.in_(scopes))

        return self.db_session.execute(stmt).scalars().all()
