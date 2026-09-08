from collections.abc import Sequence

from app import utils
from app.db.models.client import ClientEntity
from app.db.models.organization import OrganizationEntity
from app.db.models.scope import ScopeEntity
from app.services.exceptions import ScopesNotGrantedError


class ScopeService:
    @staticmethod
    def make_client_scope_from_org(
        org: OrganizationEntity, client: ClientEntity, new_scopes: list[str]
    ) -> list[ScopeEntity]:

        client_scope_map = {s.name: s for s in client.scopes} if client.scopes else {}
        org_scope_map = {s.name: s for s in org.scopes} if org.scopes else {}
        target = []
        for s in new_scopes:
            if s in client_scope_map:
                existing_scope = client_scope_map[s]
                target.append(existing_scope)
                continue

            if s in org_scope_map:
                new_client_scope = org_scope_map[s]
                target.append(new_client_scope)

        return target

    @staticmethod
    def validate_requested_scopes(existing: Sequence[ScopeEntity], incoming: list[str]) -> bool:
        existing_set = {s.name for s in existing}
        incoming_set = set(incoming)

        return incoming_set.issubset(existing_set)

    @staticmethod
    def assert_scopes_granted(organization: OrganizationEntity, requested: list[str]) -> None:
        available = [c.name for c in organization.scopes]
        if not utils.is_subset(available, requested):
            ungranted = set(requested) - set(available or [])
            raise ScopesNotGrantedError(ungranted)
