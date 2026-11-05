from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import QueryableAttribute, selectinload

from app.db.decorator import repository
from app.db.models.base import CommonColumns
from app.db.models.certificate import CertificateEntity
from app.db.models.client import ClientEntity
from app.db.models.organization import OrganizationEntity
from app.db.models.source import SourceEntity
from app.db.repository.base import RepositoryBase
from app.db.repository.contexts.organization_context import (
    OrganizationClientQueryContext,
    OrganizationQueryContext,
)
from app.db.repository.filters import HasConditions, any_matching, conditions_of, narrowed, not_deleted
from app.models.ura import UraNumber


@repository(OrganizationEntity)
class OrganizationRepository(RepositoryBase):
    def add_one(self, data: OrganizationEntity) -> OrganizationEntity:
        try:
            self.db_session.add(data)
            self.db_session.commit()
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
            select(OrganizationEntity)
            .options(
                selectinload(OrganizationEntity.scopes),
                selectinload(OrganizationEntity.certificates),
                selectinload(OrganizationEntity.sources),
                selectinload(OrganizationEntity.clients).selectinload(ClientEntity.scopes),
                selectinload(OrganizationEntity.clients).selectinload(ClientEntity.certificates),
                selectinload(OrganizationEntity.clients).selectinload(ClientEntity.sources),
            )
            .where(OrganizationEntity.id == id)
        )
        if include_deleted is False:
            stmt = stmt.where(OrganizationEntity.deleted_at.is_(None))

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

    def exsits_by_external_id(self, external_id: UraNumber) -> bool:
        stmt = select(
            select(OrganizationEntity.external_id)
            .where(
                and_(OrganizationEntity.external_id == external_id, OrganizationEntity.deleted_at.is_(None)),
            )
            .exists()
        )
        return bool(self.db_session.execute(stmt).scalar())

    def find(
        self,
        ctx: OrganizationQueryContext,
        include_deleted: bool = False,
    ) -> OrganizationEntity | None:
        """
        Will automatically load children once a parameter is present.
        """
        options = [selectinload(OrganizationEntity.scopes)]
        if ctx.certificate_ctx:
            certificates = self._narrowed(
                OrganizationEntity.certificates, ctx.certificate_ctx, CertificateEntity, include_deleted
            )
            options.append(selectinload(certificates))

        if ctx.source_ctx:
            sources = self._narrowed(OrganizationEntity.sources, ctx.source_ctx, SourceEntity, include_deleted)
            options.append(selectinload(sources))

        if ctx.client_ctx:
            options.extend(self._client_loader_options(ctx.client_ctx, include_deleted))

        stmt = (
            select(OrganizationEntity)
            .where(*ctx.get_conditions(), *not_deleted(OrganizationEntity, include_deleted))
            .options(*options)
        )
        return self.db_session.execute(stmt).unique().scalar_one_or_none()

    def find_many(
        self,
        ctx: OrganizationQueryContext,
        include_deleted: bool = False,
    ) -> Sequence[OrganizationEntity]:
        stmt = (
            select(OrganizationEntity)
            .options(*self._list_loader_options(include_deleted))
            .where(
                *ctx.get_conditions(),
                *not_deleted(OrganizationEntity, include_deleted),
                *any_matching(
                    OrganizationEntity.certificates,
                    conditions_of(ctx.certificate_ctx),
                    CertificateEntity,
                    include_deleted,
                ),
                *any_matching(OrganizationEntity.sources, conditions_of(ctx.source_ctx), SourceEntity, include_deleted),
                *self._client_filter(ctx.client_ctx, include_deleted),
            )
        )
        return self.db_session.execute(stmt).scalars().unique().all()

    @staticmethod
    def _narrowed[E: CommonColumns](
        relationship: QueryableAttribute[list[E]], ctx: HasConditions, entity: type[E], include_deleted: bool
    ) -> QueryableAttribute[list[E]]:
        return narrowed(relationship, [*ctx.get_conditions(), *not_deleted(entity, include_deleted)])

    def _client_loader_options(self, client_ctx: OrganizationClientQueryContext, include_deleted: bool) -> list[Any]:
        clients = self._narrowed(OrganizationEntity.clients, client_ctx, ClientEntity, include_deleted)
        options = [selectinload(clients).selectinload(ClientEntity.scopes)]

        if client_ctx.certificate_ctx:
            certificates = self._narrowed(
                ClientEntity.certificates, client_ctx.certificate_ctx, CertificateEntity, include_deleted
            )
            options.append(selectinload(clients).selectinload(certificates))

        if client_ctx.source_ctx:
            sources = self._narrowed(ClientEntity.sources, client_ctx.source_ctx, SourceEntity, include_deleted)
            options.append(selectinload(clients).selectinload(sources))

        return options

    @staticmethod
    def _list_loader_options(include_deleted: bool) -> list[Any]:
        clients = narrowed(OrganizationEntity.clients, not_deleted(ClientEntity, include_deleted))
        return [
            selectinload(OrganizationEntity.scopes),
            selectinload(narrowed(OrganizationEntity.certificates, not_deleted(CertificateEntity, include_deleted))),
            selectinload(narrowed(OrganizationEntity.sources, not_deleted(SourceEntity, include_deleted))),
            selectinload(clients).selectinload(ClientEntity.scopes),
            selectinload(clients).selectinload(
                narrowed(ClientEntity.certificates, not_deleted(CertificateEntity, include_deleted))
            ),
            selectinload(clients).selectinload(
                narrowed(ClientEntity.sources, not_deleted(SourceEntity, include_deleted))
            ),
        ]

    @staticmethod
    def _client_filter(client_ctx: OrganizationClientQueryContext | None, include_deleted: bool) -> list[Any]:
        if client_ctx is None:
            return []
        client_conditions = [
            *client_ctx.get_conditions(),
            *any_matching(
                ClientEntity.certificates,
                conditions_of(client_ctx.certificate_ctx),
                CertificateEntity,
                include_deleted,
            ),
            *any_matching(ClientEntity.sources, conditions_of(client_ctx.source_ctx), SourceEntity, include_deleted),
        ]
        return any_matching(OrganizationEntity.clients, client_conditions, ClientEntity, include_deleted)
