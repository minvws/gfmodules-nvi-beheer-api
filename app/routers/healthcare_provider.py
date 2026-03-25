import logging
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Response

from app.container import get_healthcare_provider_service
from app.models.healthcare_provider import (
    HealthcareProvider,
    HealthcareProviderCreate,
    HealthcareProviderUpdate,
)
from app.services.healthcare_provider import HeatlhcareProviderService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/healthcare-providers", tags=["Healthcare Providers"])


@router.post("", response_model=HealthcareProvider, response_model_exclude_none=True)
def add_one_provider(
    data: Annotated[HealthcareProviderCreate, Body()],
    service: Annotated[HeatlhcareProviderService, Depends(get_healthcare_provider_service)],
) -> Any:
    new_provider = service.create_one(**data.model_dump())
    return new_provider


@router.get("/{id}", response_model=HealthcareProvider, response_model_exclude_none=True)
def get_by_id(
    id: UUID,
    service: Annotated[HeatlhcareProviderService, Depends(get_healthcare_provider_service)],
) -> Any:
    return service.get_one(id)


@router.delete("/{id}")
def delete_by_id(
    id: UUID,
    service: Annotated[HeatlhcareProviderService, Depends(get_healthcare_provider_service)],
) -> Any:
    deleted_data = service.delete_one(id)
    if deleted_data is None:
        raise HTTPException(status_code=404)

    return Response(status_code=204)


@router.put("/{id}", response_model=HealthcareProvider, response_model_exclude_none=True)
def update(
    id: UUID,
    body: HealthcareProviderUpdate,
    service: Annotated[HeatlhcareProviderService, Depends(get_healthcare_provider_service)],
) -> Any:

    result = service.update_one(id, **body.model_dump())
    if result is None:
        raise HTTPException(status_code=404)

    return result
