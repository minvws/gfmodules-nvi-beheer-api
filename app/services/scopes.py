# from app.db.models.client_scope import ClientScopeEntity
from typing import Sequence

from app.db.models.organization import OrganizationEntity
from app.db.models.scope import ScopeEntity


class ScopeService:
    def __init__(self, allowed_scopes: set[str]) -> None:
        self.allowed_scopes = allowed_scopes

    @staticmethod
    def make_client_scope_from_org(org: OrganizationEntity, client: list[str]) -> list[ScopeEntity]:
        target = [s for s in org.scopes if s.name in client] if org.scopes else []
        return target
        # return [ClientScopeEntity(scope=s) for s in target]

    def check_incoming_scope(self, scopes: list[str]) -> bool:
        scopes_set = set(scopes)
        return scopes_set.issubset(self.allowed_scopes)

    @staticmethod
    def validate_requested_scopes(exitsting: Sequence[ScopeEntity], incoming: list[str]) -> bool:
        existing_set = set([s.name for s in exitsting])
        incoming_set = set(incoming)

        return incoming_set.issubset(existing_set)

    @staticmethod
    def make_scope_subset(main: Sequence[ScopeEntity], incoming: list[str]) -> list[ScopeEntity]:
        return [s for s in main if s.name in incoming]
