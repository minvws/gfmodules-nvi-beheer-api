from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from app.container import get_org_scopes_service
from app.models.organization import OrganizationUpdate
from app.models.scopes import ScopeAssign, ScopeUnassign
from app.services.scopes.org_scopes import OrganizationScopesService

router = APIRouter(prefix="/organizations/{organization_id}/scopes", tags=["Organization Scopes"])


@router.post("", response_model=OrganizationUpdate)
def assign_one(
    organization_id: UUID,
    data: ScopeAssign,
    service: Annotated[OrganizationScopesService, Depends(get_org_scopes_service)],
) -> Any:
    return service.assign_one(organization_id, data.scope)


@router.delete("")
def unassing_one(
    organization_id: UUID,
    data: Annotated[ScopeUnassign, Query()],
    service: Annotated[OrganizationScopesService, Depends(get_org_scopes_service)],
) -> Any:
    service.unassign_one(organization_id, data.scope)
    return Response(status_code=204)
