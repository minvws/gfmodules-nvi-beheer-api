import logging
from uuid import UUID

import gfmodules.logging as gflog

from app import utils
from app.db.db import Database
from app.db.models.organization import OrganizationEntity
from app.db.models.source import SourceEntity
from app.db.repository.client import ClientRepository
from app.db.repository.contexts.client_context import ClientQueryContext, ClientSourceQueryContext
from app.db.repository.contexts.organization_context import (
    OrganizationClientQueryContext,
    OrganizationQueryContext,
    OrganizationSourceQueryContext,
)
from app.db.repository.organization import OrganizationRepository
from app.exceptions import ConflictError, ForbiddenOperationError, RecordNotFoundError
from app.logging.audit import source_fields
from app.logging.events import Log
from app.models.source import Source, SourceCreate, SourceQueryParams, SourceUpdate

logger = logging.getLogger(__name__)


class ClientSourceService:
    def __init__(self, db: Database) -> None:
        self.db = db

    def get_one(self, organization_id: UUID, client_id: UUID, id: UUID) -> Source | None:
        with self.db.get_db_session() as session:
            org_repo = session.get_repository(OrganizationRepository)
            if not org_repo.exists(organization_id):
                raise RecordNotFoundError(organization_id)

            repo = session.get_repository(ClientRepository)
            ctx = ClientQueryContext(
                id=client_id, organization_id=organization_id, source_ctx=ClientSourceQueryContext(id=id)
            )
            client = repo.find(ctx)
            if client is None:
                raise RecordNotFoundError(client_id)

            if not client.sources:
                raise RecordNotFoundError(id)

            source = client.sources[0]
            return Source.from_entity(source)

    def get_many(self, organization_id: UUID, client_id: UUID, params: SourceQueryParams) -> list[Source]:
        with self.db.get_db_session() as session:
            org_repo = session.get_repository(OrganizationRepository)
            if not org_repo.exists(organization_id):
                raise RecordNotFoundError(organization_id)

            repo = session.get_repository(ClientRepository)
            ctx = ClientQueryContext(
                id=client_id,
                organization_id=organization_id,
                source_ctx=ClientSourceQueryContext(source_id=params.source_id, name=params.name),
            )
            client = repo.find(ctx)
            if client is None:
                raise RecordNotFoundError(client_id)

            return [Source.from_entity(e) for e in client.sources]

    def assign_one(self, organization_id: UUID, client_id: UUID, id: UUID) -> Source:
        with self.db.get_db_session(commit=True) as session:
            org_repo = session.get_repository(OrganizationRepository)
            src_ctx = OrganizationSourceQueryContext(id=id)
            ctx = OrganizationQueryContext(
                id=organization_id,
                client_ctx=OrganizationClientQueryContext(id=client_id, source_ctx=src_ctx),
                source_ctx=src_ctx,
            )

            org = org_repo.find(ctx)
            if org is None:
                raise RecordNotFoundError(organization_id)

            if not org.clients:
                raise RecordNotFoundError(client_id)

            if not org.sources:
                raise RecordNotFoundError(id)

            client = org.clients[0]
            if client.sources:
                raise ConflictError(f"Source {id} is already assigned to client {client_id}")

            target_source = org.sources[0]
            client.sources.append(target_source)
            session.commit()
            assigned = Source.from_entity(target_source)

        gflog.emit(
            logger,
            Log.CLIENT_SOURCE_ASSIGNED,
            "Source assigned to client",
            fields={**source_fields(assigned), "client_id": str(client_id)},
        )
        return assigned

    def unassign_one(self, organization_id: UUID, client_id: UUID, id: UUID) -> Source:
        with self.db.get_db_session() as session:
            org_repo = session.get_repository(OrganizationRepository)

            src_ctx = OrganizationSourceQueryContext(id=id)
            ctx = OrganizationQueryContext(
                id=organization_id,
                client_ctx=OrganizationClientQueryContext(id=client_id, source_ctx=src_ctx),
                source_ctx=src_ctx,
            )
            org = org_repo.find(ctx)
            if org is None:
                raise RecordNotFoundError(organization_id)

            if not org.clients:
                raise RecordNotFoundError(client_id)

            if not org.sources:
                raise RecordNotFoundError(id)

            client = org.clients[0]
            if not client.sources:
                raise RecordNotFoundError(f"Client {client_id} has no source {id} assigned")

            target = client.sources.pop(0)
            session.commit()
            unassigned = Source.from_entity(target)

        gflog.emit(
            logger,
            Log.CLIENT_SOURCE_UNASSIGNED,
            "Source unassigned from client",
            fields={**source_fields(unassigned), "client_id": str(client_id)},
        )
        return unassigned

    @staticmethod
    def get_client_sources_from_org(
        org: OrganizationEntity, sources: list[SourceUpdate] | list[SourceCreate]
    ) -> list[SourceEntity]:
        org_source_keys = [s.source_id for s in org.sources] if org.sources else []
        client_source_keys = [s.source_id for s in sources]

        if not utils.is_subset(org_source_keys, client_source_keys):
            raise ForbiddenOperationError("Client sources are not allowed to be assigned")

        return [s for s in org.sources if s.source_id in client_source_keys] if org.sources else []
