from enum import StrEnum

from pydantic import BaseModel


class AuthorizationScope(StrEnum):
    READ = "nvi:read"
    CREATE = "nvi:create"
    DELETE = "nvi:delete"
    LOCALIZE = "nvi:localize"


class ScopesField(BaseModel):
    scope: AuthorizationScope


class ScopeAssign(ScopesField):
    pass


class ScopeUnassign(ScopesField):
    pass
