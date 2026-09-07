from typing import NamedTuple, Sequence
from uuid import UUID

from sqlalchemy import select, tuple_
from sqlalchemy.exc import SQLAlchemyError

from app.db.decorator import repository
from app.db.models.certificate import CertificateEntity
from app.db.repository.base import RepositoryBase
from app.db.repository.query_builder.certificate_query_builder import CertificateQueryBuilder
from app.db.repository.query_builder.context.certificate_context import CertificateQueryContext
from app.db.repository.query_builder.context.data import LoadStrategy


class CertificateIndexLookup(NamedTuple):
    organization_identifier: str
    domain: str


@repository(CertificateEntity)
class CertificateRepository(RepositoryBase):
    def add_one(self, data: CertificateEntity) -> CertificateEntity:
        try:
            self.db_session.add(data)
            self.db_session.commit()
            self.db_session.session.refresh(data)
            return data
        except SQLAlchemyError:
            self.db_session.rollback()
            raise

    def exists(self, data: CertificateIndexLookup | list[CertificateIndexLookup]) -> bool:
        stmt = select(
            select(CertificateEntity)
            .where(tuple_(CertificateEntity.organization_identifier, CertificateEntity.domain).in_(data))
            .exists()
        )

        return bool(self.db_session.execute(stmt).scalar())

    def find_one(self, id: UUID, organization_id: UUID) -> CertificateEntity | None:
        stmt = CertificateQueryBuilder().with_id(id).with_organization_id(organization_id).build()
        return self.db_session.execute(stmt).scalar()

    def find_many(
        self,
        ctx: CertificateQueryContext,
        organization_id: UUID | None = None,
        include_deleted: bool = False,
    ) -> Sequence[CertificateEntity]:
        load_strategy = self._determine_strategy(ctx)
        stmt = (
            CertificateQueryBuilder(load_strategy=load_strategy, include_deleted=include_deleted)
            .with_organization_id(organization_id)
            .apply_context(ctx)
            .build()
        )

        return self.db_session.execute(stmt).scalars().all()

    def find(self, id: UUID, ctx: CertificateQueryContext, include_deleted: bool = False) -> CertificateEntity | None:
        stmt = CertificateQueryBuilder(include_deleted=include_deleted).with_id(id).apply_context(ctx).build()

        return self.db_session.execute(stmt).scalar_one_or_none()

    def _determine_strategy(self, ctx: CertificateQueryContext) -> LoadStrategy:
        org_ctx, client_ctx = ctx.organization_ctx, ctx.client_ctx
        children_conditions = []

        if org_ctx:
            children_conditions.extend([v for v in org_ctx.to_dict()])

        if client_ctx:
            children_conditions.extend([v for v in client_ctx.to_dict()])

        return (
            LoadStrategy.OUTERJOIN_LOAD
            if any(v is not None for v in children_conditions)
            else LoadStrategy.SELECTIN_LOAD
        )
