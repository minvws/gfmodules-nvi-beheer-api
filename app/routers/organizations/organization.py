from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query
from fastapi.responses import Response

from app.container import get_organization_service
from app.logging.context import organization_in_context
from app.models.organization import (
    Organization,
    OrganizationCreate,
    OrganizationQueryParams,
    OrganizationUpdate,
)
from app.services.organization import OrganizationService

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.post(
    "",
    response_model=Organization,
    response_model_exclude_none=True,
    status_code=201,
)
def register(
    data: Annotated[OrganizationCreate, Body()],
    service: Annotated[OrganizationService, Depends(get_organization_service)],
) -> Any:
    result = service.create_one(data)
    return result


@router.get(
    "/{organization_id}",
    dependencies=[Depends(organization_in_context)],
    response_model=Organization,
    response_model_exclude_none=True,
)
def get_by_id(
    organization_id: UUID,
    service: Annotated[OrganizationService, Depends(get_organization_service)],
) -> Any:
    result = service.get_one(organization_id)
    return result


@router.get("", response_model=list[Organization], response_model_exclude_none=True)
def get_many(
    params: Annotated[OrganizationQueryParams, Query()],
    service: Annotated[OrganizationService, Depends(get_organization_service)],
) -> Any:
    orgs = service.get_many(params)
    return orgs


@router.put(
    "/{organization_id}",
    dependencies=[Depends(organization_in_context)],
    response_model=OrganizationUpdate,
    response_model_exclude_none=True,
)
def update(
    organization_id: UUID,
    body: OrganizationUpdate,
    service: Annotated[OrganizationService, Depends(get_organization_service)],
) -> Any:
    result = service.update_one(organization_id, dto=body)
    return result


@router.delete("/{organization_id}", dependencies=[Depends(organization_in_context)])
def delete(
    organization_id: UUID,
    service: Annotated[OrganizationService, Depends(get_organization_service)],
) -> Any:
    service.delete_one(organization_id)
    return Response(status_code=204)
