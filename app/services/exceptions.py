class ScopesNotGrantedError(Exception):
    def __init__(self, ungranted: set[str]) -> None:
        super().__init__(f"Scopes not granted by the organization: {', '.join(sorted(ungranted))}")


class OrganizationHasActiveClientsError(Exception):
    def __init__(self, organization_id: object) -> None:
        super().__init__(f"Organization {organization_id} has active clients and cannot be deleted.")
