import logging
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.container import get_client_certificate_service
from app.models.certificates import Certificate, ClientCertificateQueryParams
from app.services.certificate.client_certificate import ClientCertificateService

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/organizations/{organization_id}/clients/{client_id}/certificate", tags=["Client Certificates"]
)


@router.get("")
def get_many_for_clients(
    organization_id: UUID,
    client_id: UUID,
    params: Annotated[ClientCertificateQueryParams, Query()],
    service: Annotated[ClientCertificateService, Depends(get_client_certificate_service)],
) -> Any:
    return service.get_many(organization_id, client_id, params)


@router.post("/{id}", response_model=Certificate)
def assign(
    organization_id: UUID,
    client_id: UUID,
    id: UUID,
    service: Annotated[ClientCertificateService, Depends(get_client_certificate_service)],
) -> Any:
    return service.assign_one(organization_id, client_id, id)


@router.get("/{id}", response_model=Certificate)
def get_one_for_client(
    organization_id: UUID,
    client_id: UUID,
    id: UUID,
    service: Annotated[ClientCertificateService, Depends(get_client_certificate_service)],
) -> Any:
    return service.get_one(organization_id, client_id, id)


@router.delete("/{id}")
def unassigne_one_for_clients(
    organization_id: UUID,
    client_id: UUID,
    id: UUID,
    service: Annotated[ClientCertificateService, Depends(get_client_certificate_service)],
) -> Any:
    return service.unassign_one(organization_id, client_id, id)
