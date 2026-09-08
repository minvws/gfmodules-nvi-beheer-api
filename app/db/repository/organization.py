from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.exc import SQLAlchemyError

from app.db.decorator import repository
from app.db.models.organization import OrganizationEntity
from app.db.repository.base import RepositoryBase
from app.db.repository.query_builder.context.organization_context import (
    OrganizationCertificateQueryContext,
    OrganizationClientQueryContext,
    OrganizationQueryContext,
    OrganizationSourceQueryContext,
)
from app.db.repository.query_builder.data import LoadStrategy
from app.db.repository.query_builder.organization_query_builder import (
    OrganizationQueryBuilder,
)


@repository(OrganizationEntity)
class OrganizationRepository(RepositoryBase):
    def add_one(self, data: OrganizationEntity) -> OrganizationEntity:
        try:
            self.db_session.add(data)
            self.db_session.commit()
            self.db_session.session.refresh(
                data,
                attribute_names=["scopes", "certificates", "sources", "clients"],
            )
            return data
        except SQLAlchemyError:
            self.db_session.rollback()
            raise

    def find_one(
        self,
        id: UUID,
        include_deleted: bool = False,
    ) -> OrganizationEntity | None:
        stmt = (
            OrganizationQueryBuilder(include_deleted=include_deleted)
            .with_id(id)
            .include_clients(OrganizationClientQueryContext.default())
            .include_scopes()
            .include_sources(OrganizationSourceQueryContext.default())
            .include_certificate(OrganizationCertificateQueryContext.default())
            .build()
        )

        return self.db_session.execute(stmt).unique().scalar()

    def exists(self, id: UUID) -> bool:
        stmt = select(
            select(OrganizationEntity.id)
            .where(
                and_(OrganizationEntity.id == id, OrganizationEntity.deleted_at.is_(None)),
            )
            .exists()
        )
        return bool(self.db_session.execute(stmt).scalar())

    def find(
        self,
        ctx: OrganizationQueryContext,
        include_delete: bool = False,
    ) -> OrganizationEntity | None:
        """
        Will automatically load children once a parameter is present.
        """
        stmt = OrganizationQueryBuilder(include_deleted=include_delete).apply_context(ctx).build()
        return self.db_session.execute(stmt).scalar_one_or_none()

    def find_many(
        self,
        ctx: OrganizationQueryContext,
        include_deleted: bool = False,
    ) -> Sequence[OrganizationEntity]:
        load_strategy = self._determine_strategy(ctx)
        stmt = (
            OrganizationQueryBuilder(load_strategy=load_strategy, include_deleted=include_deleted)
            .apply_context(ctx)
            .build()
        )

        return self.db_session.execute(stmt).scalars().unique().all()

    def _determine_strategy(self, ctx: OrganizationQueryContext) -> LoadStrategy:
        src_ctx, crt_ctx, client_ctx = ctx.source_ctx, ctx.certificate_ctx, ctx.client_ctx
        children_conditions = []
        if src_ctx:
            children_conditions.extend([v for v in src_ctx.to_dict().values()])

        if crt_ctx:
            children_conditions.extend([v for v in crt_ctx.to_dict().values()])

        if client_ctx:
            children_conditions.extend([client_ctx.name, client_ctx.description])

            c_src_ctx, c_crt_ctx = client_ctx.source_ctx, client_ctx.certificate_ctx

            if c_src_ctx:
                children_conditions.extend([v for v in c_src_ctx.to_dict().values()])

            if c_crt_ctx:
                children_conditions.extend([v for v in c_crt_ctx.to_dict().values()])

        return (
            LoadStrategy.OUTERJOIN_LOAD
            if any(v is not None for v in children_conditions)
            else LoadStrategy.SELECTIN_LOAD
        )
