import logging
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException

from app.container import get_client_service
from app.models.client import ClientResolveRequest
from app.services.client import ClientService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/clients", tags=["Clients"])


@router.post("/resolve", response_model=str, status_code=200)
def resolve(
    data: Annotated[ClientResolveRequest, Body()],
    service: Annotated[ClientService, Depends(get_client_service)],
) -> Any:
    scopes = service.resolve(
        oin=data.oin,
        common_name=data.common_name,
        mandate_id=data.mandate_id,
    )
    if scopes is None:
        raise HTTPException(status_code=404, detail="Client not found.")

    return scopes
