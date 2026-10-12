import logging
from datetime import UTC, datetime
from uuid import UUID

from app.db.db import Database
from app.db.models.client import ClientEntity
from app.db.repository.client import ClientRepository
from app.db.repository.contexts.client_context import (
    ClientCertificateQueryContext,
    ClientQueryContext,
    ClientSourceQueryContext,
)
from app.db.repository.contexts.organization_context import (
    OrganizationCertificateQueryContext,
    OrganizationClientQueryContext,
    OrganizationQueryContext,
    OrganizationSourceQueryContext,
)
from app.db.repository.organization import OrganizationRepository
from app.models.client import (
    Client,
    ClientCreate,
    ClientQueryParams,
    ClientResolveRequest,
    ClientResolveResponse,
    ClientUpdate,
)
from app.models.scopes import AuthorizationScope
from app.services.certificate import ClientCertificateService
from app.services.exceptions import EntityHasActiveMembersError, RecordNotFoundError, ResolveError
from app.services.scopes import ScopeService
from app.services.source.client_source import ClientSourceService

logger = logging.getLogger(__name__)

SOURCE_INDEPENDENT_SCOPES = frozenset({AuthorizationScope.LOCALIZE})


class ClientService:
    def __init__(
        self,
        db: Database,
    ) -> None:
        self.db = db

    def create_one(self, organization_id: UUID, dto: ClientCreate) -> Client:
        with self.db.get_db_session(commit=True) as session:
            org_repo = session.get_repository(OrganizationRepository)
            org = org_repo.find_one(organization_id)
            if not org:
                raise RecordNotFoundError(f"Organization with id {organization_id} does not exist.")

            target = ClientEntity(name=dto.name, description=dto.description, organization_id=organization_id)
            if dto.scopes:
                ScopeService.assert_scopes_granted(org, dto.scopes)
                target_scope = ScopeService.make_client_scope_from_org(org, target, dto.scopes)
                target.scopes = target_scope

            if dto.certificates:
                client_certs = ClientCertificateService.get_client_certs_from_org(org, dto.certificates)
                target.certificates = client_certs

            if dto.sources:
                client_sources = ClientSourceService.get_client_sources_from_org(org, dto.sources)
                target.sources = client_sources

            client_repo = session.get_repository(ClientRepository)
            new_client = client_repo.add_one(target)

            return Client.from_entity(new_client)

    def get_one(self, id: UUID, organization_id: UUID) -> Client:
        with self.db.get_db_session() as session:
            org_repo = session.get_repository(OrganizationRepository)
            if not org_repo.exists(organization_id):
                raise RecordNotFoundError(organization_id)

            repo = session.get_repository(ClientRepository)
            client = repo.find_one(id, organization_id)
            if client is None:
                raise RecordNotFoundError(id)

            return Client.from_entity(client)

    def get_many(
        self,
        organization_id: UUID,
        params: ClientQueryParams,
    ) -> list[Client]:
        with self.db.get_db_session() as session:
            org_repo = session.get_repository(OrganizationRepository)
            if not org_repo.exists(organization_id):
                raise RecordNotFoundError(organization_id)

            ctx = ClientQueryContext(
                organization_id=organization_id,
                name=params.name,
                scopes=params.scopes if params.scopes else None,
                source_ctx=ClientSourceQueryContext(source_id=params.source_id, name=params.source_name),
                certificate_ctx=ClientCertificateQueryContext(
                    organization_identifier=params.cert_organization_identifier, domain=params.cert_domain
                ),
            )
            clients_repo = session.get_repository(ClientRepository)
            clients = clients_repo.find_many(ctx, params.include_deleted)

            return [Client.from_entity(c) for c in clients]

    def update_one(
        self,
        id: UUID,
        organization_id: UUID,
        dto: ClientUpdate,
    ) -> Client:
        with self.db.get_db_session(commit=True) as session:
            org_repo = session.get_repository(OrganizationRepository)
            ctx = OrganizationQueryContext(
                id=organization_id,
                client_ctx=OrganizationClientQueryContext(
                    id=id,
                    source_ctx=OrganizationSourceQueryContext.default(),
                    certificate_ctx=OrganizationCertificateQueryContext.default(),
                ),
                source_ctx=OrganizationSourceQueryContext.default(),
                certificate_ctx=OrganizationCertificateQueryContext.default(),
            )
            org = org_repo.find(ctx)
            if org is None:
                raise RecordNotFoundError(organization_id)

            client = org.clients[0] if org.clients else None
            if client is None:
                raise RecordNotFoundError(id)

            if dto.name:
                client.name = dto.name
            if dto.description:
                client.description = dto.description

            if dto.scopes:
                ScopeService.assert_scopes_granted(org, dto.scopes)
                updated_scopes = ScopeService.make_client_scope_from_org(org, client, dto.scopes)
                client.scopes = updated_scopes
            else:
                client.scopes = []

            if dto.sources:
                updated_sources = ClientSourceService.get_client_sources_from_org(org, dto.sources)
                client.sources = updated_sources
            else:
                client.sources = []

            if dto.certificates:
                updated_certs = ClientCertificateService.get_client_certs_from_org(org, dto.certificates)
                client.certificates = updated_certs
            else:
                client.certificates = []
            session.flush()

            return Client.from_entity(client)

    def delete_one(self, id: UUID, organization_id: UUID) -> None:
        with self.db.get_db_session(commit=True) as session:
            org_repo = session.get_repository(OrganizationRepository)
            if not org_repo.exists(organization_id):
                raise RecordNotFoundError(organization_id)

            client_repo = session.get_repository(ClientRepository)
            client = client_repo.find_one(id, organization_id)
            if client is None:
                raise RecordNotFoundError(id)

            active_member = self.validate_for_delete(client)
            if active_member:
                raise EntityHasActiveMembersError("Client", active_member, id)

            client.deleted_at = datetime.now(UTC)

    def resolve(self, request: ClientResolveRequest) -> ClientResolveResponse:
        with self.db.get_db_session() as session:
            client_repo = session.get_repository(ClientRepository)
            client = client_repo.find_for_resolve(
                request.client_id,
                request.organization_external_id,
                request.certificate_organization_identifier,
                request.certificate_domains,
                request.source_id,
            )
            if client is None or not client.certificates:
                raise ResolveError

            if request.source_id is not None and not client.sources:
                raise ResolveError

            scope_names = {s.name for s in client.scopes}
            if request.source_id is None:
                scope_names &= SOURCE_INDEPENDENT_SCOPES  # keeps only the elements present in both sets

            return ClientResolveResponse(
                scopes=" ".join(sorted(scope_names)),
                organization_name=client.organization.name,
                matched_domain=client.certificates[0].domain,
            )

    @staticmethod
    def validate_for_delete(client: ClientEntity) -> str | None:
        if any(c.deleted_at is None for c in client.certificates):
            return "Certificates"

        if any(s.deleted_at is None for s in client.sources):
            return "Sources"

        return None
