import logging
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.container import get_client_source_service
from app.models.source import Source, SourceQueryParams
from app.services.source.client_source import ClientSourceService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/organizations/{organization_id}/clients/{client_id}/sources", tags=["Client Sources"])


@router.get("", response_model=list[Source])
def get_many(
    organization_id: UUID,
    client_id: UUID,
    params: Annotated[SourceQueryParams, Query()],
    service: Annotated[ClientSourceService, Depends(get_client_source_service)],
) -> Any:
    return service.get_many(organization_id, client_id, params)


@router.get("/{id}", response_model=Source)
def get_one(
    organization_id: UUID,
    client_id: UUID,
    id: UUID,
    service: Annotated[ClientSourceService, Depends(get_client_source_service)],
) -> Any:
    return service.get_one(organization_id, client_id, id)


@router.post("/{id}", response_model=Source)
def assigne_one(
    organization_id: UUID,
    client_id: UUID,
    id: UUID,
    service: Annotated[ClientSourceService, Depends(get_client_source_service)],
) -> Any:
    return service.assign_one(organization_id, client_id, id)


@router.delete("/{id}", response_model=Source)
def unassign_one(
    organization_id: UUID,
    client_id: UUID,
    id: UUID,
    service: Annotated[ClientSourceService, Depends(get_client_source_service)],
) -> Any:
    return service.unassign_one(organization_id, client_id, id)
