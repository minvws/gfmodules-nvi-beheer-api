import logging
from typing import Annotated, Any, List
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.exc import IntegrityError

from app.container import get_client_service, get_organization_service
from app.models.client import Client, ClientCreate, ClientQueryParams, ClientUpdate
from app.services.client import ClientService
from app.services.exceptions import ScopesNotGrantedError
from app.services.organization import OrganizationService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/organizations/{organization_id}/clients", tags=["Clients"])


def get_organization_or_404(
    organization_id: UUID,
    organization_service: Annotated[OrganizationService, Depends(get_organization_service)],
) -> None:
    if not organization_service.exists(organization_id):
        raise HTTPException(status_code=404, detail="Organization not found.")


@router.post(
    "",
    response_model=Client,
    response_model_exclude_none=True,
    status_code=201,
    dependencies=[Depends(get_organization_or_404)],
)
def register(
    organization_id: UUID,
    data: Annotated[ClientCreate, Body()],
    service: Annotated[ClientService, Depends(get_client_service)],
) -> Any:
    try:
        return service.create_one(organization_id=organization_id, **data.model_dump())
    except ScopesNotGrantedError as error:
        raise HTTPException(status_code=422, detail=str(error))
    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="A client with this mandate_id is already registered for this organization.",
        )


@router.get(
    "/{id}",
    response_model=Client,
    response_model_exclude_none=True,
    dependencies=[Depends(get_organization_or_404)],
)
def get_by_id(
    organization_id: UUID,
    id: UUID,
    service: Annotated[ClientService, Depends(get_client_service)],
) -> Any:
    result = service.get_one(id, organization_id)
    if result is None:
        raise HTTPException(status_code=404)
    return result


@router.get(
    "",
    response_model=List[Client],
    response_model_exclude_none=True,
    dependencies=[Depends(get_organization_or_404)],
)
def get_many(
    organization_id: UUID,
    params: Annotated[ClientQueryParams, Query()],
    service: Annotated[ClientService, Depends(get_client_service)],
) -> Any:
    return service.get_many(organization_id=organization_id, **params.model_dump())


@router.put(
    "/{id}",
    response_model=Client,
    response_model_exclude_none=True,
    dependencies=[Depends(get_organization_or_404)],
)
def update(
    organization_id: UUID,
    id: UUID,
    body: ClientUpdate,
    service: Annotated[ClientService, Depends(get_client_service)],
) -> Any:
    try:
        result = service.update_one(id, organization_id, **body.model_dump(exclude_unset=True))
    except ScopesNotGrantedError as error:
        raise HTTPException(status_code=422, detail=str(error))
    if result is None:
        raise HTTPException(status_code=404)
    return result


@router.delete(
    "/{id}",
    dependencies=[Depends(get_organization_or_404)],
)
def delete(
    organization_id: UUID,
    id: UUID,
    service: Annotated[ClientService, Depends(get_client_service)],
) -> Response:
    result = service.delete_one(id, organization_id)
    if result is None:
        raise HTTPException(status_code=404)
    return Response(status_code=204)
