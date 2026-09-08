from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from app.db.decorator import repository
from app.db.models.client import ClientEntity
from app.db.models.organization import OrganizationEntity
from app.db.repository.base import RepositoryBase
from app.db.repository.query_builder.client_query_builder import ClientQueryBuilder
from app.db.repository.query_builder.context.client_context import (
    ClientCertificateQueryContext,
    ClientQueryContext,
    ClientSourceQueryContext,
)
from app.db.repository.query_builder.data import LoadStrategy
from app.models.oin import Oin
from app.models.ura import UraNumber


@repository(ClientEntity)
class ClientRepository(RepositoryBase):
    def add_one(self, data: ClientEntity) -> ClientEntity:
        try:
            self.db_session.add(data)
            self.db_session.commit()
            self.db_session.session.refresh(data, attribute_names=["scopes", "certificates", "sources"])
            return data
        except SQLAlchemyError:
            self.db_session.rollback()
            raise

    def find_one(self, id: UUID, organization_id: UUID) -> ClientEntity | None:
        stmt = (
            ClientQueryBuilder()
            .with_id(id)
            .with_organization_id(organization_id)
            .include_scopes()
            .include_certificate(ClientCertificateQueryContext.default())
            .include_sources(ClientSourceQueryContext.default())
            .build()
        )
        return self.db_session.execute(stmt).scalar_one_or_none()

    def find_many(self, ctx: ClientQueryContext, include_deleted: bool = False) -> Sequence[ClientEntity]:
        load_strategy = self._determine_strategy(ctx)
        stmt = (
            ClientQueryBuilder(load_strategy=load_strategy, include_deleted=include_deleted).apply_context(ctx).build()
        )
        return self.db_session.execute(stmt).scalars().unique().all()

    def _determine_strategy(self, ctx: ClientQueryContext) -> LoadStrategy:
        children_conditions = []
        src_ctx, crt_ctx = ctx.source_ctx, ctx.certificate_ctx
        if src_ctx:
            children_conditions.extend([v for v in src_ctx.to_dict().values()])

        if crt_ctx:
            children_conditions.extend([v for v in crt_ctx.to_dict().values()])

        return (
            LoadStrategy.OUTERJOIN_LOAD
            if any(v is not None for v in children_conditions)
            else LoadStrategy.SELECTIN_LOAD
        )

    def find(
        self,
        ctx: ClientQueryContext,
    ) -> ClientEntity | None:

        stmt = ClientQueryBuilder().apply_context(ctx).build()
        return self.db_session.execute(stmt).scalar_one_or_none()

    def get_by_credentials(self, common_name: str, oin: Oin, org_ura: UraNumber) -> ClientEntity | None:
        stmt = (
            select(ClientEntity)
            .join(
                OrganizationEntity,
                ClientEntity.organization_id == OrganizationEntity.id,
            )
            .where(
                and_(
                    ClientEntity.common_name == common_name,
                    ClientEntity.oin == oin,
                    OrganizationEntity.register_id == org_ura,
                    OrganizationEntity.deleted_at.is_(None),
                    ClientEntity.deleted_at.is_(None),
                )
            )
            .options(joinedload(ClientEntity.organization))
        )
        return self.db_session.execute(stmt).scalar()
