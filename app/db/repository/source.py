from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import selectinload

from app.db.decorator import repository
from app.db.models.source import SourceEntity
from app.db.repository.base import RepositoryBase
from app.db.repository.contexts.source_context import SourceQueryContext


@repository(SourceEntity)
class SourceRepository(RepositoryBase):
    def find_many_by_external_ids(self, external_id: list[str]) -> Sequence[SourceEntity]:
        stmt = select(SourceEntity).where(
            and_(SourceEntity.deleted_at.is_(None), SourceEntity.source_id.in_(external_id))
        )
        return self.db_session.execute(stmt).scalars().all()

    def find_one(self, id: UUID, organization_id: UUID, include_deleted: bool = False) -> SourceEntity | None:
        stmt = select(SourceEntity).where(SourceEntity.id == id, SourceEntity.organization_id == organization_id)
        if include_deleted is False:
            stmt = stmt.where(SourceEntity.deleted_at.is_(None))

        return self.db_session.execute(stmt).scalar_one_or_none()

    def find_many(self, ctx: SourceQueryContext, include_deleted: bool = False) -> Sequence[SourceEntity]:
        stmt = select(SourceEntity)
        root_filter = ctx.get_conditions()
        if include_deleted is False:
            root_filter.append(SourceEntity.deleted_at.is_(None))

        if root_filter:
            stmt = stmt.where(*root_filter)

        return self.db_session.execute(stmt).scalars().unique().all()

    def find(self, ctx: SourceQueryContext, include_deleted: bool = False) -> SourceEntity | None:
        stmt = select(SourceEntity)
        options = []

        root_filter = ctx.get_conditions()
        if include_deleted is False:
            root_filter.append(SourceEntity.deleted_at.is_(None))

        if root_filter:
            stmt = stmt.where(*root_filter)

        if ctx.organization_ctx:
            org_attr: Any = SourceEntity.organization
            org_ctx = ctx.organization_ctx
            org_filters = org_ctx.get_conditions()
            if org_filters:
                org_attr = org_attr.and_(*org_filters)

            options.append(selectinload(org_attr))

        if ctx.client_ctx:
            client_attr: Any = SourceEntity.clients
            client_ctx = ctx.client_ctx
            client_filters = client_ctx.get_conditions()
            if client_filters:
                client_attr = client_attr.and_(*client_filters)

            options.append(selectinload(client_attr))

        if options:
            stmt = stmt.options(*options)

        return self.db_session.execute(stmt).unique().scalar_one_or_none()
