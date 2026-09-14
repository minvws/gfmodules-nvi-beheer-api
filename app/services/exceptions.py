# TODO: make specific errors for these generics
from fastapi.exceptions import HTTPException


class ScopesNotGrantedError(HTTPException):
    def __init__(self, ungranted: set[str]) -> None:
        super().__init__(
            status_code=403, detail=f"Scopes not granted by the organization: {', '.join(sorted(ungranted))}"
        )


class ScopeNotAllowedError(HTTPException):
    def __init__(self, request_scope: list[str], allowed_scopes: list[str]) -> None:
        forbidden_scope = set(request_scope) - set(allowed_scopes)
        super().__init__(status_code=403, detail=f"Scope `{', '.join(forbidden_scope)}` is not allowed")


class EntityHasActiveMemebersError(HTTPException):
    def __init__(self, entity: str, member: str, entity_id: object) -> None:
        super().__init__(status_code=403, detail=f"{entity} {entity_id} has active {member} and cannot be deleted.")


class RecordNotFoundError(HTTPException):
    def __init__(self, record_id: object) -> None:
        super().__init__(status_code=404, detail=f"Record {record_id} not found")


class ConflictError(HTTPException):
    def __init__(self, msg: str | None = None) -> None:
        _msg = msg if msg else "record already exists"
        super().__init__(status_code=409, detail=msg)


class ForbidenOperationError(HTTPException):
    def __init__(self, msg: str | None = None) -> None:
        _msg = msg if msg else "Operation is not allowed"
        super().__init__(status_code=409, detail=msg)
