"""
Domain exceptions raised by the service layer.
"""

from app.models.scopes import AuthorizationScope


class DomainError(Exception):
    """Base class for errors the service layer reports to its callers."""

    message: str = "Request could not be processed"
    reason: str = "request_refused"

    def __init__(self, message: str | None = None) -> None:
        if message is not None:
            self.message = message
        super().__init__(self.message)


class ScopesNotGrantedError(DomainError):
    """A client requests scopes its organization has not been granted."""

    reason = "scopes_not_granted"

    def __init__(self, ungranted: set[AuthorizationScope]) -> None:
        self.ungranted = ungranted
        ungranted_values = sorted(s.value for s in ungranted)
        super().__init__(f"Scopes not granted by the organization: {', '.join(ungranted_values)}")


class EntityHasActiveMembersError(DomainError):
    """The entity cannot be deleted while it still has active members."""

    reason = "entity_has_active_members"

    def __init__(self, entity: str, member: str, entity_id: object) -> None:
        super().__init__(f"{entity} {entity_id} has active {member} and cannot be deleted.")


class RecordNotFoundError(DomainError):
    reason = "record_not_found"

    def __init__(self, record_id: object) -> None:
        super().__init__(f"Record {record_id} not found")


class ConflictError(DomainError):
    reason = "conflict"
    message = "record already exists"


class ForbiddenOperationError(DomainError):
    reason = "forbidden_operation"
    message = "Operation is not allowed"


class ResolveError(DomainError):
    """No client matches the organization, certificate and client id of a resolve request."""

    reason = "resolve_denied"
    message = "Client authorization does not exist for given parameters"
