import logging
from typing import Annotated, Any
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
        result = service.create_one(organization_id, data)
        return result
    except ScopesNotGrantedError as error:
        raise HTTPException(status_code=422, detail=str(error))
    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="A client with this oin and common_name is already registered for this organization.",
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
    return result


@router.get(
    "",
    response_model=list[Client],
    response_model_exclude_none=True,
    dependencies=[Depends(get_organization_or_404)],
)
def get_many(
    organization_id: UUID,
    params: Annotated[ClientQueryParams, Query()],
    service: Annotated[ClientService, Depends(get_client_service)],
) -> Any:
    results = service.get_many(
        organization_id=organization_id,
        oin=params.oin,
        common_name=params.common_name,
        source_id=params.source_id,
        scopes=params.sanatized_scope,
    )
    return [Client.from_entity(e) for e in results]


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
        result = service.update_one(
            id=id,
            organization_id=organization_id,
            common_name=body.common_name,
            oin=body.external_id,
            source_id=body.source_id,
            scopes=body.sanatized_scopes,
        )
    except ScopesNotGrantedError as error:
        raise HTTPException(status_code=422, detail=str(error))
    if result is None:
        raise HTTPException(status_code=404)
    return Client.from_entity(result)


@router.delete(
    "/{id}",
    dependencies=[Depends(get_organization_or_404)],
)
def delete(
    organization_id: UUID,
    id: UUID,
    service: Annotated[ClientService, Depends(get_client_service)],
) -> Response:
    service.delete_one(id, organization_id)
    return Response(status_code=204)
