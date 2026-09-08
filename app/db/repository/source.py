from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import and_, select

from app.db.decorator import repository
from app.db.models.source import SourceEntity
from app.db.repository.base import RepositoryBase
from app.db.repository.query_builder.context.source_context import SourceQueryContext
from app.db.repository.query_builder.data import LoadStrategy
from app.db.repository.query_builder.source_query_builder import SourceQueryBuilder


@repository(SourceEntity)
class SourceRepository(RepositoryBase):
    def find_many_by_external_ids(self, external_id: list[str]) -> Sequence[SourceEntity]:
        stmt = select(SourceEntity).where(
            and_(SourceEntity.deleted_at.is_(None), SourceEntity.source_id.in_(external_id))
        )
        return self.db_session.execute(stmt).scalars().all()

    def find_one(self, id: UUID, organization_id: UUID) -> SourceEntity | None:
        stmt = SourceQueryBuilder().with_id(id).with_organization_id(organization_id).build()
        return self.db_session.execute(stmt).scalar_one_or_none()

    def find_many(self, ctx: SourceQueryContext) -> Sequence[SourceEntity]:
        load_strategy = self._determine_strategy(ctx)
        stmt = SourceQueryBuilder(load_strategy=load_strategy).apply_context(ctx).build()

        return self.db_session.execute(stmt).scalars().unique().all()

    def find(self, ctx: SourceQueryContext) -> SourceEntity | None:
        stmt = SourceQueryBuilder().apply_context(ctx).build()

        return self.db_session.execute(stmt).scalar_one_or_none()

    def _determine_strategy(self, ctx: SourceQueryContext) -> LoadStrategy:
        org_ctx, client_ctx = ctx.organization_ctx, ctx.client_ctx
        children_conditions = []

        if org_ctx:
            children_conditions.extend([v for v in org_ctx.to_dict().values()])

        if client_ctx:
            children_conditions.extend([v for v in client_ctx.to_dict().values()])

        return (
            LoadStrategy.OUTERJOIN_LOAD
            if any(v is not None for v in children_conditions)
            else LoadStrategy.SELECTIN_LOAD
        )
