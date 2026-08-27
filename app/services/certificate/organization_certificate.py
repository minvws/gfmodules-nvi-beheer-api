from datetime import datetime
from uuid import UUID

from app.db.db import Database
from app.db.models.certificate import CertificateEntity
from app.db.models.organization import OrganizationEntity
from app.db.repository.certificate import CertificateRepository
from app.db.repository.organization import OrganizationRepository
from app.models.certificates import Certificate, CertificateCreate, CertificateQueryParams, CertificateUpdate
from app.services.exceptions import ConflictError, RecordNotFoundError


class OrganizationCertificateService:
    def __init__(self, database: Database) -> None:
        self.db = database

    def get_one(self, id: UUID, organization_id: UUID) -> Certificate:
        with self.db.get_db_session() as session:
            repo = session.get_repository(CertificateRepository)
            result = repo.find_one(id, organization_id)
            if result is None:
                raise RecordNotFoundError(id)

            return Certificate.from_entity(result)

    def get_many(self, organization_id: UUID, params: CertificateQueryParams) -> list[Certificate]:
        with self.db.get_db_session() as session:
            repo = session.get_repository(CertificateRepository)
            results = repo.find_many(organization_id=organization_id, **params.model_dump())

            return [Certificate.from_entity(e) for e in results]

    def create_one(self, organization_id: UUID, dto: CertificateCreate) -> Certificate:
        with self.db.get_db_session() as session:
            # org_repo = session.get_repository(OrganizationRepository)
            # org_exists = org_repo.exists(organization_id)
            # if org_exists is False:
            #     raise RecordNotFoundError(organization_id)
            #
            # cert_repo = session.get_repository(CertificateRepository)
            # cert_exists = cert_repo.exists(dto.into_index_lookup())
            # if cert_exists:
            #     raise ConflictError(
            #         f"Certificate with organization_identifier: {dto.organization_identifier}, domain: {dto.domain} already exists"
            #     )
            #
            # new_cert = cert_repo.add_one(
            #     CertificateEntity(**dto.model_dump(exclude_unset=True), organization_id=organization_id)
            # )
            # return Certificate.from_entity(new_cert)
            org_repo = session.get_repository(OrganizationRepository)
            org = org_repo.find_one(organization_id)
            if org is None:
                raise RecordNotFoundError(organization_id)

            cert_exists = (
                any(dto.make_unique_key(org.id) == c.unique_key for c in org.certificates)
                if org.certificates
                else False
            )
            if cert_exists:
                raise ConflictError(
                    f"Certificate with organization_identifier: {dto.organization_identifier}, domain: {dto.domain} already exists"
                )
            new_cert = CertificateEntity(**dto.model_dump())
            if org.certificates:
                org.certificates.append(new_cert)
            else:
                org.certificates = [new_cert]

            session.commit()

            return Certificate.from_entity(new_cert)

    def update_one(self, id: UUID, organization_id: UUID, dto: CertificateUpdate) -> Certificate:
        with self.db.get_db_session() as session:
            repo = session.get_repository(CertificateRepository)
            target = repo.find_one(id, organization_id)
            if target is None:
                raise RecordNotFoundError(id)

            if CertificateUpdate.from_entity(target) == dto:
                return Certificate.from_entity(target)

            if target.organization_identifier != dto.organization_identifier:
                target.organization_identifier = dto.organization_identifier

            if target.domain != target.domain:
                target.domain = target.domain

            session.commit()
            return Certificate.from_entity(target)

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
