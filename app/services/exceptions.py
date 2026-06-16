class ScopesNotGrantedError(Exception):
    def __init__(self, ungranted: set[str]) -> None:
        super().__init__(f"Scopes not granted by the organization: {', '.join(sorted(ungranted))}")
