from collections.abc import Sequence

from app.db.db import Database
from app.db.models.client import ClientEntity
from app.db.models.organization import OrganizationEntity
from app.db.models.scope import ScopeEntity


class ScopeService:
    def __init__(self, db: Database) -> None:
        self.db = db

    @staticmethod
    def make_client_scope_from_org(
        org: OrganizationEntity, client: ClientEntity, new_scopes: list[str]
    ) -> list[ScopeEntity]:

        client_scope_map = {s.name: s for s in client.scopes}
        org_scope_map = {s.name: s for s in org.scopes}
        target = []
        for s in new_scopes:
            if s in client_scope_map.keys():
                existing_scope = client_scope_map[s]
                target.append(existing_scope)
                continue

            if s in org_scope_map.keys():
                new_client_scope = org_scope_map[s]
                target.append(new_client_scope)

        return target

    @staticmethod
    def validate_requested_scopes(existing: Sequence[ScopeEntity], incoming: list[str]) -> bool:
        existing_set = {s.name for s in existing}
        incoming_set = set(incoming)

        return incoming_set.issubset(existing_set)

    @staticmethod
    def make_scope_subset(main: Sequence[ScopeEntity], incoming: list[str]) -> list[ScopeEntity]:
        return [s for s in main if s.name in incoming]
