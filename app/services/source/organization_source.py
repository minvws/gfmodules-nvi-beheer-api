import datetime
from uuid import UUID

from app.db.db import Database
from app.db.models.source import SourceEntity
from app.db.repository.contexts.organization_context import (
    OrganizationQueryContext,
    OrganizationSourceQueryContext,
)
from app.db.repository.contexts.source_context import SourceClientQueryContext, SourceQueryContext
from app.db.repository.organization import OrganizationRepository
from app.db.repository.source import SourceRepository
from app.models.source import Source, SourceCreate, SourceQueryParams, SourceUpdate
from app.services.exceptions import (
    ConflictError,
    EntityHasActiveMembersError,
    RecordNotFoundError,
)


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
                raise ConflictError(f"Organization {org.id} already has a source {dto.source_id} assigned")

            new_source = dto.into_entity(org.id)
            org.sources.append(new_source)

            session.session.flush()
            return Source.from_entity(new_source)

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
                target.source_id = dto.source_id

            if target.name != dto.name:
                target.name = dto.name

            session.flush()
            return Source.from_entity(target)

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

            return Source.from_entity(target)

    @staticmethod
    def validate_for_delete(source: SourceEntity) -> str | None:
        if any(c.deleted_at is None for c in source.clients):
            return "Clients"

        return None
