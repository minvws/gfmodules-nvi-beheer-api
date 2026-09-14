# TODO: make specific errors for these generics


class ScopesNotGrantedError(Exception):
    def __init__(self, ungranted: set[str]) -> None:
        super().__init__(f"Scopes not granted by the organization: {', '.join(sorted(ungranted))}")


class ScopeNotAllowedError(Exception):
    def __init__(self, request_scope: list[str], allowed_scopes: list[str]) -> None:
        forbidden_scope = set(request_scope) - set(allowed_scopes)
        super().__init__(f"Scope `{', '.join(forbidden_scope)}` is not allowed")


class EntityHasActiveMemebersError(Exception):
    def __init__(self, entity: str, member: str, entity_id: object) -> None:
        super().__init__(f"{entity} {entity_id} has active {member} and cannot be deleted.")


class RecordNotFoundError(Exception):
    def __init__(self, record_id: object) -> None:
        super().__init__(f"Record {record_id} not found")


class ConflictError(Exception):
    def __init__(self, msg: str | None = None) -> None:
        _msg = msg if msg else "record already exists"
        super().__init__(msg)


class ForbidenOperationError(Exception):
    def __init__(self, msg: str | None = None) -> None:
        _msg = msg if msg else "Operation is not allowed"
        super().__init__(msg)
