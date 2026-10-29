import datetime
import logging
from uuid import UUID

import gfmodules.logging as gflog
from sqlalchemy.exc import IntegrityError

from app.db.db import Database
from app.db.models.source import SourceEntity
from app.db.repository.contexts.organization_context import (
    OrganizationQueryContext,
    OrganizationSourceQueryContext,
)
from app.db.repository.contexts.source_context import SourceClientQueryContext, SourceQueryContext
from app.db.repository.organization import OrganizationRepository
from app.db.repository.source import SourceRepository
from app.exceptions import (
    ConflictError,
    EntityHasActiveMembersError,
    RecordNotFoundError,
)
from app.logging.audit import source_fields
from app.logging.events import Log
from app.models.source import Source, SourceCreate, SourceQueryParams, SourceUpdate

logger = logging.getLogger(__name__)


class OrganizationSourceService:
    def __init__(self, db: Database) -> None:
        self.db = db

    def get_one(self, organization_id: UUID, id: UUID) -> Source:
        with self.db.get_db_session() as session:
            org_repo = session.get_repository(OrganizationRepository)
            if not org_repo.exists(organization_id):
                raise RecordNotFoundError(organization_id)

            source_repo = session.get_repository(SourceRepository)
            source = source_repo.find_one(id, organization_id)
            if source is None:
                raise RecordNotFoundError(id)

            return Source.from_entity(source)

    def get_many(self, organization_id: UUID, params: SourceQueryParams) -> list[Source]:
        with self.db.get_db_session() as session:
            org_repo = session.get_repository(OrganizationRepository)
            if not org_repo.exists(organization_id):
                raise RecordNotFoundError(organization_id)

            ctx = SourceQueryContext(source_id=params.source_id, name=params.name, organization_id=organization_id)
            source_repo = session.get_repository(SourceRepository)
            sources = source_repo.find_many(ctx)

            return [Source.from_entity(e) for e in sources]

    def create_one(self, organization_id: UUID, dto: SourceCreate) -> Source:
        with self.db.get_db_session(commit=True) as session:
            org_repo = session.get_repository(OrganizationRepository)
            ctx = OrganizationQueryContext(
                id=organization_id, source_ctx=OrganizationSourceQueryContext(source_id=dto.source_id)
            )

            org = org_repo.find(ctx)
            if org is None:
                raise RecordNotFoundError(organization_id)

            if org.sources:
                raise self._source_conflict(org.id, dto.source_id)

            new_source = dto.into_entity(org.id)
            org.sources.append(new_source)

            session.session.flush()
            source = Source.from_entity(new_source)

        gflog.emit(logger, Log.SOURCE_CREATED, "Source created", fields=source_fields(source))
        return source

    def update_one(self, organization_id: UUID, id: UUID, dto: SourceUpdate) -> Source:
        with self.db.get_db_session(commit=True) as session:
            repo = session.get_repository(OrganizationRepository)
            ctx = OrganizationQueryContext(id=organization_id, source_ctx=OrganizationSourceQueryContext(id=id))

            org = repo.find(ctx)
            if org is None:
                raise RecordNotFoundError(organization_id)

            if not org.sources:
                raise RecordNotFoundError(id)

            target = org.sources[0]
            if SourceUpdate.from_entity(target) == dto:
                return Source.from_entity(target)

            if target.source_id != dto.source_id:
                source_repo = session.get_repository(SourceRepository)
                if source_repo.find_many(SourceQueryContext(organization_id=org.id, source_id=dto.source_id)):
                    raise self._source_conflict(org.id, dto.source_id)
                target.source_id = dto.source_id

            if target.name != dto.name:
                target.name = dto.name

            try:
                session.flush()
            except IntegrityError:
                raise self._source_conflict(org.id, dto.source_id)
            updated = Source.from_entity(target)

        gflog.emit(logger, Log.SOURCE_UPDATED, "Source updated", fields=source_fields(updated))
        return updated

    def delete_one(self, organization_id: UUID, id: UUID) -> Source:
        with self.db.get_db_session(commit=True) as session:
            org_repo = session.get_repository(OrganizationRepository)
            if not org_repo.exists(organization_id):
                raise RecordNotFoundError(organization_id)

            source_repo = session.get_repository(SourceRepository)
            ctx = SourceQueryContext(
                id=id, organization_id=organization_id, client_ctx=SourceClientQueryContext.default()
            )
            target = source_repo.find(ctx)
            if target is None:
                raise RecordNotFoundError(id)

            active_members = self.validate_for_delete(target)
            if active_members is not None:
                raise EntityHasActiveMembersError("Source", active_members, target.id)

            target.deleted_at = datetime.datetime.now(datetime.UTC)
            deleted = Source.from_entity(target)

        gflog.emit(logger, Log.SOURCE_DELETED, "Source deleted", fields=source_fields(deleted))
        return deleted

    @staticmethod
    def _source_conflict(organization_id: UUID, source_id: str) -> ConflictError:
        return ConflictError(f"Organization {organization_id} already has a source {source_id} assigned")

    @staticmethod
    def validate_for_delete(source: SourceEntity) -> str | None:
        if any(c.deleted_at is None for c in source.clients):
            return "Clients"

        return None
