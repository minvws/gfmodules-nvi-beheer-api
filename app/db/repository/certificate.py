from collections.abc import Sequence
from typing import NamedTuple
from uuid import UUID

from app.db.decorator import repository
from app.db.models.certificate import CertificateEntity
from app.db.repository.base import RepositoryBase
from app.db.repository.query_builder.certificate_query_builder import CertificateQueryBuilder
from app.db.repository.query_builder.context.certificate_context import CertificateQueryContext
from app.db.repository.query_builder.data import LoadStrategy


class CertificateIndexLookup(NamedTuple):
    organization_identifier: str
    domain: str


@repository(CertificateEntity)
class CertificateRepository(RepositoryBase):
    def find_one(self, id: UUID, organization_id: UUID) -> CertificateEntity | None:
        stmt = CertificateQueryBuilder().with_id(id).with_organization_id(organization_id).build()
        return self.db_session.execute(stmt).scalar()

    def find_many(self, ctx: CertificateQueryContext, include_deleted: bool = False) -> Sequence[CertificateEntity]:
        load_strategy = self._determine_strategy(ctx)

        stmt = (
            CertificateQueryBuilder(load_strategy=load_strategy, include_deleted=include_deleted)
            .apply_context(ctx)
            .build()
        )

        return self.db_session.execute(stmt).scalars().unique().all()

    def find(self, ctx: CertificateQueryContext, include_deleted: bool = False) -> CertificateEntity | None:
        stmt = CertificateQueryBuilder(include_deleted=include_deleted).apply_context(ctx).build()

        return self.db_session.execute(stmt).scalar_one_or_none()

    def _determine_strategy(self, ctx: CertificateQueryContext) -> LoadStrategy:
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
