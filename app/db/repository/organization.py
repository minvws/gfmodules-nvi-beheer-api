from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import ColumnElement, and_, select, update
from sqlalchemy.exc import SQLAlchemyError

from app.db.decorator import repository
from app.db.models.organization import OrganizationEntity
from app.db.repository.base import RepositoryBase
from app.db.repository.query_builder.data import OrganizationQueryContext
from app.db.repository.query_builder.organization_query_builder import (
    CertificateQueryContext,
    ClientQueryContext,
    LoadStrategy,
    OrganizationQueryBuilder,
    SourceQueryContext,
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
            .include_clients(ClientQueryContext.default())
            .include_scopes()
            .include_sources(SourceQueryContext.default())
            .include_certificate(CertificateQueryContext.default())
            .build()
        )

        return self.db_session.execute(stmt).unique().scalar()

    def exists(self, id: UUID) -> bool:
        stmt = select(select(OrganizationEntity.id).where(self._and_clause(id)).exists())
        return bool(self.db_session.execute(stmt).scalar())

    def find(
        self,
        id: UUID,
        ctx: OrganizationQueryContext,
        include_delete: bool = False,
    ) -> OrganizationEntity | None:
        """
        Will automatically load children once a parameter is present.
        """
        stmt = OrganizationQueryBuilder(include_deleted=include_delete).with_id(id).apply_context(ctx).build()
        # builder = OrganizationQueryBuilder().with_id(id).include_scopes()
        #
        # if client_id:
        #     builder = builder.include_clients(ClientQueryContext(id=client_id))
        #
        # if certificate_id:
        #     builder = builder.include_certificate(
        #         CertificateQueryContext(id=certificate_id))
        #
        # if source_id:
        #     builder = builder.include_sources(SourceQueryContext(id=source_id))
        #
        # stmt = builder.build()
        #
        # THIS IS VERY OLD
        # stmt = (
        #     OrganizationQueryBuilder()
        #     .with_id(id)
        #     .include_certificate(certificate_id)
        #     .include_clients(
        #         id=client_id,
        #         certificate_id=certificate_id,
        #         source_id=source_id,
        #         include_certificates=True,
        #         include_sources=True,
        #     )
        #     .include_sources(source_id)
        #     .include_certificate(certificate_id)
        #     .build()
        # )
        #
        # load_options = []
        # if certificate_id:
        #     load_options.append(
        #         selectinload(
        #             OrganizationEntity.certificates.and_(
        #                 CertificateEntity.id == certificate_id, CertificateEntity.deleted_at.is_(
        #                     None)
        #             )
        #         )
        #     )
        #
        # if source_id:
        #     load_options.append(
        #         selectinload(
        #             OrganizationEntity.sources.and_(
        #                 SourceEntity.id == source_id, SourceEntity.deleted_at.is_(None))
        #         )
        #     )
        #
        # if client_id:
        #     client_load_option = selectinload(
        #         OrganizationEntity.clients.and_(
        #             ClientEntity.id == client_id, ClientEntity.deleted_at.is_(None))
        #     ).selectinload(ClientEntity.scopes)
        #     if certificate_id:
        #         client_load_option = client_load_option.selectinload(
        #             ClientEntity.certificates.and_(
        #                 CertificateEntity.id == certificate_id, CertificateEntity.deleted_at.is_(
        #                     None)
        #             )
        #         )
        #
        #     if source_id:
        # client_load_option = client_load_option.selectinload(
        #             ClientEntity.sources.and_(
        #                 SourceEntity.id == source_id, SourceEntity.deleted_at.is_(None))
        #         )
        #
        #     load_options.append(client_load_option)
        #
        # stmt = select(OrganizationEntity).where(
        #     and_(OrganizationEntity.id == id,
        #          OrganizationEntity.deleted_at.is_(None))
        # )
        # if load_options:
        #     stmt = stmt.options(*load_options)

        return self.db_session.execute(stmt).scalar_one_or_none()

    # def find_many(
    #     self,
    #     external_id: UraNumber | None = None,
    #     name: str | None = None,
    #     scopes: list[str] | None = None,
    #     cert_identifier: str | None = None,
    #     cert_domain: str | None = None,
    #     include_deleted: bool = False,
    # ) -> Sequence[OrganizationEntity]:
    #     children_conditions: list[ColumnElement[bool]] = []
    #     parent_conditions: list[ColumnElement[bool]] = []
    #
    #     if not include_deleted:
    #         parent_conditions.append(OrganizationEntity.deleted_at.is_(None))
    #
    #     if external_id:
    #         parent_conditions.append(OrganizationEntity.external_id == external_id)
    #     if name:
    #         parent_conditions.append(OrganizationEntity.name == name)
    #
    #     if scopes:
    #         scopes_conditions = [(ScopeEntity.name == s) for s in scopes]
    #         children_conditions.append(or_(*scopes_conditions))
    #
    #     if cert_identifier:
    #         children_conditions.append(CertificateEntity.organization_identifier == cert_identifier)
    #
    #     if cert_domain:
    #         children_conditions.append(CertificateEntity.domain == cert_domain)
    #
    #     stmt = select(OrganizationEntity)
    #     if children_conditions:
    #         stmt = (
    #             stmt.outerjoin(OrganizationEntity.scopes)
    #             .outerjoin(OrganizationEntity.certificates.and_(CertificateEntity.deleted_at.is_(None)))
    #             .outerjoin(OrganizationEntity.sources)
    #             .options(
    #                 contains_eager(OrganizationEntity.scopes),
    #                 contains_eager(OrganizationEntity.certificates),
    #                 contains_eager(OrganizationEntity.sources),
    #             )
    #         ).where(and_(*parent_conditions, *children_conditions))
    #
    #     else:
    #         stmt = stmt.options(
    #             selectinload(OrganizationEntity.scopes),
    #             selectinload(OrganizationEntity.certificates.and_(CertificateEntity.deleted_at.is_(None))),
    #             selectinload(OrganizationEntity.sources.and_(SourceEntity.deleted_at.is_(None))),
    #         ).where(and_(*parent_conditions))
    #
    #     return self.db_session.execute(stmt).scalars().unique().all()

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
            c_src_ctx, c_crt_ctx = client_ctx.source_ctx, client_ctx.cert_ctx

            if c_src_ctx:
                children_conditions.extend([v for v in c_src_ctx.to_dict().values()])

            if c_crt_ctx:
                children_conditions.extend([v for v in c_crt_ctx.to_dict().values()])

        return (
            LoadStrategy.OUTERJOIN_LOAD
            if any(v is not None for v in children_conditions)
            else LoadStrategy.SELECTIN_LOAD
        )

    def update(self, id: UUID, **kwargs: object) -> OrganizationEntity | None:
        try:
            target = {k: kwargs[k] for k in OrganizationEntity.__table__.columns.keys() if k in kwargs}
            if not target:
                return None
            stmt = update(OrganizationEntity).where(self._and_clause(id)).values(target).returning(OrganizationEntity)
            result = self.db_session.execute(stmt).scalar_one_or_none()
            self.db_session.commit()
            return result
        except SQLAlchemyError:
            self.db_session.rollback()
            raise

    def _and_clause(self, id: UUID) -> ColumnElement[bool]:
        return and_(
            OrganizationEntity.id == id,
            OrganizationEntity.deleted_at.is_(None),
        )
