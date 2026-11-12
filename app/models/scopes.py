from enum import StrEnum


class AuthorizationScope(StrEnum):
    READ = "nvi:read"
    CREATE = "nvi:create"
    DELETE = "nvi:delete"
    LOCALIZE = "nvi:localize"
