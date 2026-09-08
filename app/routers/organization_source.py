import logging
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.container import get_organization_source_service
from app.models.source import Source, SourceCreate, SourceQueryParams, SourceUpdate
from app.services.source.organization_source import OrganizationSourceService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/organizations/{organization_id}/source", tags=["Organization Sources"])


@router.post("", response_model=Source)
def register(
    organization_id: UUID,
    body: SourceCreate,
    service: Annotated[OrganizationSourceService, Depends(get_organization_source_service)],
) -> Any:
    return service.create_one(organization_id, body)


@router.get("", response_model=list[Source])
def get_many(
    organization_id: UUID,
    params: Annotated[SourceQueryParams, Query()],
    service: Annotated[OrganizationSourceService, Depends(get_organization_source_service)],
) -> Any:
    return service.get_many(organization_id, params)


@router.get("/{id}", response_model=Source)
def get_one(
    organization_id: UUID,
    id: UUID,
    service: Annotated[OrganizationSourceService, Depends(get_organization_source_service)],
) -> Any:
    return service.get_one(organization_id, id)


@router.put("/{id}")
def update_one(
    organization_id: UUID,
    id: UUID,
    body: SourceUpdate,
    service: Annotated[OrganizationSourceService, Depends(get_organization_source_service)],
) -> Any:
    return service.update_one(organization_id, id, body)


@router.delete("/{id}")
def delete_one(
    organization_id: UUID,
    id: UUID,
    service: Annotated[OrganizationSourceService, Depends(get_organization_source_service)],
) -> Any:
    return service.delete_one(organization_id, id)
