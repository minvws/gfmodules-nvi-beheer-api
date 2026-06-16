import logging
from typing import Annotated, Any, List
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.exc import IntegrityError

from app.container import get_organization_service
from app.models.organization import Organization, OrganizationCreate, OrganizationQueryParams, OrganizationUpdate
from app.services.organization import OrganizationService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.post("", response_model=Organization, response_model_exclude_none=True, status_code=201)
def register(
    data: Annotated[OrganizationCreate, Body()],
    service: Annotated[OrganizationService, Depends(get_organization_service)],
) -> Any:
    try:
        return service.create_one(**data.model_dump())
    except IntegrityError:
        raise HTTPException(status_code=409, detail="An organization with this ID is already registered.")


@router.get("/{id}", response_model=Organization, response_model_exclude_none=True)
def get_by_id(
    id: UUID,
    service: Annotated[OrganizationService, Depends(get_organization_service)],
) -> Any:
    result = service.get_one(id)
    if result is None:
        raise HTTPException(status_code=404)
    return result


@router.get("", response_model=List[Organization], response_model_exclude_none=True)
def get_many(
    params: Annotated[OrganizationQueryParams, Query()],
    service: Annotated[OrganizationService, Depends(get_organization_service)],
) -> Any:
    return service.get_many(**params.model_dump())


@router.put("/{id}", response_model=Organization, response_model_exclude_none=True)
def update(
    id: UUID,
    body: OrganizationUpdate,
    service: Annotated[OrganizationService, Depends(get_organization_service)],
) -> Any:
    result = service.update_one(id, **body.model_dump(exclude_unset=True))
    if result is None:
        raise HTTPException(status_code=404)
    return result


@router.delete("/{id}")
def delete(
    id: UUID,
    service: Annotated[OrganizationService, Depends(get_organization_service)],
) -> Response:
    result = service.delete_one(id)
    if result is None:
        raise HTTPException(status_code=404)
    return Response(status_code=204)
