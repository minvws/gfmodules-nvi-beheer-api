import logging
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.exc import IntegrityError

from app.container import get_organization_service
from app.models.organization import (
    Organization,
    OrganizationCreate,
    OrganizationQueryParams,
    OrganizationUpdate,
)
from app.services.exceptions import OrganizationHasActiveClientsError
from app.services.organization import OrganizationService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/organizations", tags=["Organizations"])

# TODO: handle soft deleted organizations on create


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
    try:
        result = service.create_one(data)
        return result
    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="An organization with this ID is already registered.",
        )


@router.get("/{id}", response_model=Organization, response_model_exclude_none=True)
def get_by_id(
    id: UUID,
    service: Annotated[OrganizationService, Depends(get_organization_service)],
) -> Any:
    result = service.get_one(id)
    if result is None:
        raise HTTPException(status_code=404)
    return result


@router.get("", response_model=list[Organization], response_model_exclude_none=True)
def get_many(
    params: Annotated[OrganizationQueryParams, Query()],
    service: Annotated[OrganizationService, Depends(get_organization_service)],
) -> Any:
    orgs = service.get_many(**params.model_dump())
    return [Organization.from_entity(org) for org in orgs]


@router.put("/{id}", response_model=Organization, response_model_exclude_none=True)
def update(
    id: UUID,
    body: OrganizationUpdate,
    service: Annotated[OrganizationService, Depends(get_organization_service)],
) -> Any:
    result = service.update_one(id, dto=body)
    if result is None:
        raise HTTPException(status_code=404)
    return Organization.from_entity(result)


@router.delete("/{id}")
def delete(
    id: UUID,
    service: Annotated[OrganizationService, Depends(get_organization_service)],
) -> Response:
    try:
        result = service.delete_one(id)
    except OrganizationHasActiveClientsError as error:
        raise HTTPException(status_code=409, detail=str(error))
    if result is None:
        raise HTTPException(status_code=404)
    return Response(status_code=204)
