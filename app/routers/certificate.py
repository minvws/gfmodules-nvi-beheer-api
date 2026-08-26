import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.container import get_certificate_service
from app.models.certificates import CertificateCreate
from app.services.certificate import CertificateService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/organizations", tags=["Certificates"])


@router.post("/{organization_id}/certificate")
def register(
    organization_id: UUID,
    data: CertificateCreate,
    service: Annotated[CertificateService, Depends(get_certificate_service)],
):
    return service.create_one(organization_id, data)


@router.get("{organization_id}/certificate")
def get_many(): ...


@router.get("{organization_id}/certificate/{id}")
def get_by_id(): ...


@router.put("{organization_id}/certificate/{id}")
def update(): ...


@router.delete("{organization_id}/certificate/{id}")
def delete(): ...


@router.post("/{organization_id}/clients/{client_id}/certificate")
def assign(): ...


@router.get("/{organization_id}/clients/{client_id}/certificate")
def get_many_for_clients(): ...
