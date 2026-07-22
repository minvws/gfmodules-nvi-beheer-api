import logging
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.container import get_org_certificate_service
from app.models.certificates import Certificate, CertificateCreate, CertificateQueryParams, CertificateUpdate
from app.services.certificate import OrganizationCertificateService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/organizations", tags=["Certificates"])


@router.post("/{organization_id}/certificate", response_model=Certificate)
def register(
    organization_id: UUID,
    data: CertificateCreate,
    service: Annotated[OrganizationCertificateService, Depends(get_org_certificate_service)],
) -> Any:
    return service.create_one(organization_id, data)


@router.get("{organization_id}/certificate", response_model=list[Certificate], response_model_exclude_none=True)
def get_many(
    organization_id: UUID,
    params: Annotated[CertificateQueryParams, Query()],
    service: Annotated[OrganizationCertificateService, Depends(get_org_certificate_service)],
) -> Any:
    return service.get_many(organization_id, params)


@router.get("{organization_id}/certificate/{id}")
def get_by_id(
    organization_id: UUID,
    id: UUID,
    service: Annotated[OrganizationCertificateService, Depends(get_org_certificate_service)],
):
    return service.get_one(id, organization_id)


@router.put("{organization_id}/certificate/{id}")
def update(
    organization_id: UUID,
    id: UUID,
    data: CertificateUpdate,
    service: Annotated[OrganizationCertificateService, Depends(get_org_certificate_service)],
):
    return service.update_one(id, organization_id, data)


@router.delete("{organization_id}/certificate/{id}")
def delete(): ...


@router.post("/{organization_id}/clients/{client_id}/certificate")
def assign(): ...


@router.get("/{organization_id}/clients/{client_id}/certificate")
def get_many_for_clients(): ...


@router.delete("/{organization_id}/clients/{client_id}/certificate/{id}")
def delete_one_for_clients(): ...
