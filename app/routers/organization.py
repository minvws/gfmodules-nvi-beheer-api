import logging
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query
from fastapi.responses import Response

from app.container import get_organization_service
from app.models.organization import (
    Organization,
    OrganizationCreate,
    OrganizationQueryParams,
    OrganizationUpdate,
)
from app.services.organization import OrganizationService

logger = logging.getLogger(__name__)
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


@router.get("/{id}", response_model=Organization, response_model_exclude_none=True)
def get_by_id(
    id: UUID,
    service: Annotated[OrganizationService, Depends(get_organization_service)],
) -> Any:
    result = service.get_one(id)
    return result


@router.get("", response_model=list[Organization], response_model_exclude_none=True)
def get_many(
    params: Annotated[OrganizationQueryParams, Query()],
    service: Annotated[OrganizationService, Depends(get_organization_service)],
) -> Any:
    orgs = service.get_many(params)
    return orgs


@router.put("/{id}", response_model=OrganizationUpdate, response_model_exclude_none=True)
def update(
    id: UUID,
    body: OrganizationUpdate,
    service: Annotated[OrganizationService, Depends(get_organization_service)],
) -> Any:
    result = service.update_one(id, dto=body)
    return result


@router.delete("/{id}")
def delete(
    id: UUID,
    service: Annotated[OrganizationService, Depends(get_organization_service)],
) -> Any:
    service.delete_one(id)
    return Response(status_code=204)
