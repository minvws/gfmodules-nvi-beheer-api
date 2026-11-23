from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Response

from app.container import get_client_scopes_service
from app.models.client import Client
from app.models.scopes import AuthorizationScope
from app.services.scopes.client_scopes import ClientScopesService

router = APIRouter(prefix="/organizations/{organization_id}/clients/{client_id}/scope", tags=["Client Scopes"])


@router.post("/{scope}", response_model=Client)
def assign_one(
    organization_id: UUID,
    client_id: UUID,
    scope: AuthorizationScope,
    service: Annotated[ClientScopesService, Depends(get_client_scopes_service)],
) -> Any:
    return service.assign_one(organization_id, client_id, scope)


@router.delete("/{scope}")
def unassing_one(
    organization_id: UUID,
    client_id: UUID,
    scope: AuthorizationScope,
    service: Annotated[ClientScopesService, Depends(get_client_scopes_service)],
) -> Any:
    service.unassing_one(organization_id, client_id, scope)
    return Response(status_code=204)
