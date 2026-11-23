from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Response

from app.container import get_org_scopes_service
from app.models.organization import OrganizationUpdate
from app.models.scopes import AuthorizationScope
from app.services.scopes.org_scopes import OrganizationScopesService

router = APIRouter(prefix="/organizations/{organization_id}/scope", tags=["Organization Scopes"])


@router.post("/{scope}", response_model=OrganizationUpdate)
def assign_one(
    organization_id: UUID,
    scope: AuthorizationScope,
    service: Annotated[OrganizationScopesService, Depends(get_org_scopes_service)],
) -> Any:
    return service.assign_one(organization_id, scope)


@router.delete("/{scope}")
def unassing_one(
    organization_id: UUID,
    scope: AuthorizationScope,
    service: Annotated[OrganizationScopesService, Depends(get_org_scopes_service)],
) -> Any:
    service.unassign_one(organization_id, scope)
    return Response(status_code=204)
