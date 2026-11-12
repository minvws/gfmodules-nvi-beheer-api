from uuid import UUID

from app.db.db import Database
from app.db.repository.client import ClientRepository
from app.db.repository.contexts.organization_context import (
    OrganizationClientQueryContext,
    OrganizationQueryContext,
)
from app.db.repository.organization import OrganizationRepository
from app.exceptions import ConflictError, RecordNotFoundError
from app.models.client import ClientPlein
from app.models.scopes import AuthorizationScope
from app.services.scopes.utils import ScopeUtils


class ClientScopesService:
    def __init__(self, db: Database) -> None:
        self.db = db

    def assign_one(self, organization_id: UUID, id: UUID, scope: AuthorizationScope) -> ClientPlein:
        with self.db.get_db_session(commit=True) as session:
            org_repo = session.get_repository(OrganizationRepository)
            ctx = OrganizationQueryContext(
                id=organization_id,
                client_ctx=OrganizationClientQueryContext(
                    id=id,
                ),
            )

            org = org_repo.find(ctx)
            if org is None:
                raise RecordNotFoundError(organization_id)

            ScopeUtils.assert_scopes_granted(org, [scope])

            if not org.clients:
                raise RecordNotFoundError(id)

            client = org.clients[0]
            if scope in [s.name for s in client.scopes]:
                raise ConflictError(f"Client {client.id} already as scope {scope.value} assigned")

            target = next(s for s in org.scopes if s.name == scope)
            client.scopes.append(target)
            return ClientPlein.from_entity(client)

    def unassing_one(self, organization_id: UUID, id: UUID, scope: AuthorizationScope) -> None:
        with self.db.get_db_session(commit=True) as session:
            org_repo = session.get_repository(OrganizationRepository)
            org_exits = org_repo.exists(organization_id)
            if org_exits is False:
                raise RecordNotFoundError(organization_id)

            client_repo = session.get_repository(ClientRepository)
            client = client_repo.find_one(id=id, organization_id=organization_id)
            if client is None:
                raise RecordNotFoundError(id)

            if scope not in [s.name for s in client.scopes]:
                raise RecordNotFoundError(f"Client {client.id} does not have scope {scope.value}")

            target = next(s for s in client.scopes if s.name == scope)
            client.scopes.remove(target)
