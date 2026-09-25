import logging
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends

from app.container import get_client_service
from app.models.client import Client, ClientResolveRequest
from app.services.client import ClientService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/clients", tags=["Clients"])


@router.post("/resolve", response_model=Client, response_model_exclude_none=True, status_code=200)
def resolve(
    data: Annotated[ClientResolveRequest, Body()],
    service: Annotated[ClientService, Depends(get_client_service)],
) -> Any:
    client = service.resolve(
        client_id=data.client_id, organization_id=data.organization_id, sub=data.sub, common_name=data.common_name
    )

    return client
