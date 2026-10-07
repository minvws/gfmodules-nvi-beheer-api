import logging
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Response

from app.container import get_client_scopes_service
from app.models.client import Client
from app.models.scopes import ScopeAssign
from app.services.scopes.client_scopes import ClientScopesService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/organizations/{organization_id}/clients/{client_id}/scopes", tags=["Client Scopes"])


@router.post("", response_model=Client)
def assigne_one(
    organization_id: UUID,
    client_id: UUID,
    data: ScopeAssign,
    service: Annotated[ClientScopesService, Depends(get_client_scopes_service)],
) -> Any:
    return service.assigne_one(organization_id, client_id, data.scope)


@router.delete("")
def unassing_one(
    organization_id: UUID,
    client_id: UUID,
    data: ScopeAssign,
    service: Annotated[ClientScopesService, Depends(get_client_scopes_service)],
) -> Any:
    service.unassing_one(organization_id, client_id, data.scope)
    return Response(status_code=204)
