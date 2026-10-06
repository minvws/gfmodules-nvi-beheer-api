import logging
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends

from app.container import get_client_service
from app.models.client import ClientResolveRequest, ClientResolveResponse
from app.services.client import ClientService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/clients", tags=["Clients"])


@router.post("/resolve", response_model=ClientResolveResponse, response_model_exclude_none=True, status_code=200)
def resolve(
    client_resolve_request: Annotated[ClientResolveRequest, Body()],
    service: Annotated[ClientService, Depends(get_client_service)],
) -> Any:
    return service.resolve(client_resolve_request)
