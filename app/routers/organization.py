import logging
from typing import Annotated, Any, List
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


@router.post("", response_model=Organization, response_model_exclude_none=True, status_code=201)
def register(
    data: Annotated[OrganizationCreate, Body()],
    service: Annotated[OrganizationService, Depends(get_organization_service)],
) -> Any:
    try:
        result = service.create_one(register_id=data.register_id, name=data.name, scopes=data.sanitized_scopes)
        return Organization.from_entity(result)
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
    return Organization.from_entity(result)


@router.get("", response_model=List[Organization], response_model_exclude_none=True)
def get_many(
    params: Annotated[OrganizationQueryParams, Query()],
    service: Annotated[OrganizationService, Depends(get_organization_service)],
) -> Any:
    orgs = service.get_many(
        register_id=params.register_id,
        name=params.name,
        scopes=params.sanitized_scopes,
        include_deleted=params.include_deleted,
    )
    return [Organization.from_entity(org) for org in orgs]


@router.put("/{id}", response_model=Organization, response_model_exclude_none=True)
def update(
    id: UUID,
    body: OrganizationUpdate,
    service: Annotated[OrganizationService, Depends(get_organization_service)],
) -> Any:
    result = service.update_one(id=id, name=body.name, scope=body.sanitized_scopes)
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
