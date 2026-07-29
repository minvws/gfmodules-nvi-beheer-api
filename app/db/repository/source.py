from typing import Sequence

from sqlalchemy import and_, select

from app.db.decorator import repository
from app.db.models.source import SourceEntity
from app.db.repository.base import RepositoryBase


@repository(SourceEntity)
class SourceRepository(RepositoryBase):
    def find_many_by_external_ids(self, external_id: list[str]) -> Sequence[SourceEntity]:
        stmt = select(SourceEntity).where(
            and_(SourceEntity.deleted_at.is_(None), SourceEntity.source_id.in_(external_id))
        )
        return self.db_session.execute(stmt).scalars().all()
