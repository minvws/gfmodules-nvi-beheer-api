import logging
from typing import Annotated

from fastapi import APIRouter, Depends

from app.container import get_certificate_service
from app.models.certificates import CertificateCreate
from app.services.certificate import CertificateService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/organizations", tags=["Certificates"])


@router.post("/{organization_id}/certificate")
def foo(data: CertificateCreate, service: Annotated[CertificateService, Depends(get_certificate_service)]): ...
