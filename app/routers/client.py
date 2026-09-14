import logging
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query
from fastapi.responses import Response

from app.container import get_client_service
from app.models.client import Client, ClientCreate, ClientQueryParams, ClientUpdate
from app.services.client import ClientService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/organizations/{organization_id}/clients", tags=["Clients"])


@router.post(
    "",
    response_model=Client,
    response_model_exclude_none=True,
    status_code=201,
)
def register(
    organization_id: UUID,
    data: Annotated[ClientCreate, Body()],
    service: Annotated[ClientService, Depends(get_client_service)],
) -> Any:
    result = service.create_one(organization_id, data)
    return result


@router.get(
    "/{id}",
    response_model=Client,
    response_model_exclude_none=True,
)
def get_by_id(
    organization_id: UUID,
    id: UUID,
    service: Annotated[ClientService, Depends(get_client_service)],
) -> Any:
    result = service.get_one(id, organization_id)
    return result


@router.get(
    "",
    response_model=list[Client],
    response_model_exclude_none=True,
)
def get_many(
    organization_id: UUID,
    params: Annotated[ClientQueryParams, Query()],
    service: Annotated[ClientService, Depends(get_client_service)],
) -> Any:
    results = service.get_many(
        organization_id=organization_id,
        params=params,
    )
    return results


@router.put(
    "/{id}",
    response_model=Client,
    response_model_exclude_none=True,
)
def update(
    organization_id: UUID,
    id: UUID,
    body: ClientUpdate,
    service: Annotated[ClientService, Depends(get_client_service)],
) -> Any:
    result = service.update_one(
        id=id,
        organization_id=organization_id,
        dto=body,
    )
    return result


@router.delete(
    "/{id}",
)
def delete(
    organization_id: UUID,
    id: UUID,
    service: Annotated[ClientService, Depends(get_client_service)],
) -> Response:
    service.delete_one(id, organization_id)
    return Response(status_code=204)
