class ScopesNotGrantedError(Exception):
    def __init__(self, ungranted: set[str]) -> None:
        super().__init__(f"Scopes not granted by the organization: {', '.join(sorted(ungranted))}")


class ScopeNotAllowedError(Exception):
    def __init__(self, scope: list[str]) -> None:
        super().__init__(f"Scope `{', '.join(scope)}` is not allowed")


class OrganizationHasActiveClientsError(Exception):
    def __init__(self, organization_id: object) -> None:
        super().__init__(f"Organization {organization_id} has active clients and cannot be deleted.")


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
