from uuid import UUID

from app.db.db import Database
from app.db.repository.contexts.organization_context import OrganizationClientQueryContext, OrganizationQueryContext
from app.db.repository.organization import OrganizationRepository
from app.db.repository.scope import ScopeRepository
from app.models.organization import Organization
from app.models.scopes import AuthorizationScope
from app.services.exceptions import ConflictError, RecordNotFoundError


class OrganizationScopesService:
    def __init__(self, db: Database) -> None:
        self.db = db

    def assigne_one(self, id: UUID, scope: AuthorizationScope) -> Organization:
        with self.db.get_db_session(commit=True) as session:
            repo = session.get_repository(OrganizationRepository)
            org = repo.find_one(id)
            if org is None:
                raise RecordNotFoundError(id)

            if scope in [s.name for s in org.scopes]:
                raise ConflictError(f"Organization `{org.id}` already has scope `{scope.value}`")

            scope_repo = session.get_repository(ScopeRepository)
            app_scopes = scope_repo.find_many()
            org_scope = next(s for s in app_scopes if s.name == scope)
            org.scopes.append(org_scope)

            return Organization.from_entity(org)

    def unassigne_one(self, id: UUID, scope: AuthorizationScope) -> None:
        with self.db.get_db_session(commit=True) as session:
            repo = session.get_repository(OrganizationRepository)
            ctx = OrganizationQueryContext(id=id, client_ctx=OrganizationClientQueryContext(scopes=[scope]))

            org = repo.find(ctx)
            if org is None:
                raise RecordNotFoundError(id)

            if scope not in [s.name for s in org.scopes]:
                raise RecordNotFoundError(f"Organization `{org.id}` does not have `{scope.value}`")

            if org.clients:
                clients_ids = ", ".join([str(c.id) for c in org.clients])
                raise ConflictError(f"Organization {org.id} has Clients with scope `{scope.value}`: {clients_ids}")

            scope_repo = session.get_repository(ScopeRepository)
            app_scopes = scope_repo.find_many()
            target = next(s for s in app_scopes if s.name == scope)

            org.scopes.remove(target)
