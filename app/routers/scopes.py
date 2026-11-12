from typing import Any

from fastapi import APIRouter

from app.models.scopes import AuthorizationScope

router = APIRouter(prefix="/scopes", tags=["Scopes"])


@router.get("", description="Get the list of available scopes in the application")
def get_avaialbe_scope() -> Any:
    scopes = [s.value for s in AuthorizationScope]
    return scopes
