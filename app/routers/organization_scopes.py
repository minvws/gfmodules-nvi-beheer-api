import logging
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Response

from app.container import get_org_scopes_service
from app.models.organization import Organization
from app.models.scopes import ScopeAssign
from app.services.scopes.org_scopes import OrganizationScopesService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/organizations/{organization_id}/scopes", tags=["Organization Scopes"])


@router.post("", response_model=Organization)
def assigne_one(
    organization_id: UUID,
    data: ScopeAssign,
    service: Annotated[OrganizationScopesService, Depends(get_org_scopes_service)],
) -> Any:
    return service.assigne_one(organization_id, data.scope)


@router.delete("")
def unassinge_one(
    organization_id: UUID,
    data: ScopeAssign,
    service: Annotated[OrganizationScopesService, Depends(get_org_scopes_service)],
) -> Any:
    service.unassigne_one(organization_id, data.scope)
    return Response(status_code=204)
