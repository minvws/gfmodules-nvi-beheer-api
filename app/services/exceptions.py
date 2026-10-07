from fastapi.exceptions import HTTPException

from app.models.scopes import AuthorizationScope


class ScopesNotGrantedError(HTTPException):
    def __init__(self, ungranted: set[AuthorizationScope]) -> None:
        ungranted_value_set = {s.value for s in ungranted}
        super().__init__(
            status_code=403, detail=f"Scopes not granted by the organization: {', '.join(sorted(ungranted_value_set))}"
        )


class EntityHasActiveMembersError(HTTPException):
    def __init__(self, entity: str, member: str, entity_id: object) -> None:
        super().__init__(status_code=403, detail=f"{entity} {entity_id} has active {member} and cannot be deleted.")


class RecordNotFoundError(HTTPException):
    def __init__(self, record_id: object | str) -> None:
        super().__init__(status_code=404, detail=f"Record {record_id} not found")


class ConflictError(HTTPException):
    def __init__(self, msg: str | None = None) -> None:
        _msg = msg if msg else "record already exists"
        super().__init__(status_code=409, detail=_msg)


class ForbidenOperationError(HTTPException):
    def __init__(self, msg: str | None = None) -> None:
        _msg = msg if msg else "Operation is not allowed"
        super().__init__(status_code=403, detail=_msg)


class ResolveError(HTTPException):
    def __init__(self) -> None:
        _msg = "Client authorization does not exist for given parameters"
        super().__init__(status_code=404, detail=_msg)
