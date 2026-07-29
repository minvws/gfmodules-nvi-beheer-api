from datetime import datetime
from uuid import UUID

from app import utils
from app.db.db import Database
from app.db.models.certificate import CertificateEntity
from app.db.models.organization import OrganizationEntity
from app.db.repository.certificate import CertificateRepository
from app.db.repository.organization import OrganizationRepository
from app.models.certificates import Certificate, CertificateCreate, CertificateUpdate
from app.services.exceptions import ConflictError, ForbidenOperationError, RecordNotFoundError


class CertificateService:
    def __init__(self, db: Database) -> None:
        self.db = db

    def create_one(self, organization_id: UUID, dto: CertificateCreate) -> Certificate:
        with self.db.get_db_session() as session:
            org_repo = session.get_repository(OrganizationRepository)
            org_exists = org_repo.exists(organization_id)
            if org_exists is False:
                raise RecordNotFoundError(organization_id)

            cert_repo = session.get_repository(CertificateRepository)
            cert_exists = cert_repo.exists(dto.into_index_lookup())
            if cert_exists:
                raise ConflictError(
                    f"Certificate with organization_identifier: {dto.organization_identifier}, domain: {dto.domain} already exists"
                )

            new_cert = cert_repo.add_one(
                CertificateEntity(**dto.model_dump(exclude_unset=True), organization_id=organization_id)
            )
            return Certificate.from_entity(new_cert)

    @staticmethod
    def compute_certs_to_update_from_org(
        org: OrganizationEntity, target: list[CertificateUpdate]
    ) -> list[CertificateEntity]:
        current_certs_map = {c.unique_key: c for c in org.certificates} if org.certificates else {}
        update_certs: list[CertificateEntity] = []
        if not current_certs_map:
            update_certs = [
                CertificateEntity(
                    organization_identifier=c.organization_identifier, domain=c.domain, organization_id=org.id
                )
                for c in target
            ]
        else:
            for incoming_cert in target:
                # TODO: this should be a function in dto
                unique_key = f"{org.id}-{incoming_cert.organization_identifier}-{incoming_cert.domain}"
                if unique_key in current_certs_map:
                    cert = current_certs_map[unique_key]
                    update_certs.append(cert)
                else:
                    new_cert = CertificateEntity(**incoming_cert.model_dump(exclude_unset=True), organization_id=org.id)
                    update_certs.append(new_cert)

        # handle soft delete
        update_list = [c.unique_key for c in update_certs]
        for key, value in current_certs_map.items():
            if key not in update_list:
                value.deleted_at = datetime.now()
                update_certs.append(value)

        return update_certs

    @staticmethod
    def get_client_certs_from_org(org: OrganizationEntity, certs: list[CertificateCreate]) -> list[CertificateEntity]:
        org_cert_keys = [c.unique_key for c in org.certificates] if org.certificates else []
        client_cert_keys = [c.make_unique_key(org.id) for c in certs]
        if not utils.is_subset(org_cert_keys, client_cert_keys):
            raise ForbidenOperationError("Client certs are not allowed to be assigned")

        return [c for c in org.certificates if c.unique_key in client_cert_keys] if org.certificates else []
