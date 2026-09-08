from datetime import datetime
from uuid import UUID

from app.db.db import Database
from app.db.models.certificate import CertificateEntity
from app.db.models.organization import OrganizationEntity
from app.db.repository.certificate import CertificateRepository
from app.db.repository.organization import OrganizationRepository
from app.db.repository.query_builder.context.certificate_context import (
    CertificateClientQueryContext,
    CertificateQueryContext,
)
from app.db.repository.query_builder.context.organization_context import (
    OrganizationCertificateQueryContext,
    OrganizationQueryContext,
)
from app.models.certificates import (
    Certificate,
    CertificateCreate,
    CertificateQueryParams,
    CertificateUpdate,
)
from app.services.exceptions import ConflictError, ForbidenOperationError, RecordNotFoundError


class OrganizationCertificateService:
    def __init__(self, database: Database) -> None:
        self.db = database

    def get_one(self, id: UUID, organization_id: UUID) -> Certificate:
        with self.db.get_db_session() as session:
            org_repo = session.get_repository(OrganizationRepository)
            if not org_repo.exists(organization_id):
                raise RecordNotFoundError(organization_id)

            cert_repo = session.get_repository(CertificateRepository)
            cert = cert_repo.find_one(id, organization_id)
            if cert is None:
                raise RecordNotFoundError(id)

            return Certificate.from_entity(cert)

    def get_many(self, organization_id: UUID, params: CertificateQueryParams) -> list[Certificate]:
        with self.db.get_db_session() as session:
            org_repo = session.get_repository(OrganizationRepository)
            if not org_repo.exists(organization_id):
                raise RecordNotFoundError(organization_id)

            ctx = params.into_certificate_query_context()
            cert_repo = session.get_repository(CertificateRepository)
            # TODO: check this if it can be generalized
            certs = cert_repo.find_many_per_organization(organization_id, ctx, params.include_deleted)

            return [Certificate.from_entity(c) for c in certs]

    def create_one(self, organization_id: UUID, dto: CertificateCreate) -> Certificate:
        with self.db.get_db_session() as session:
            org_repo = session.get_repository(OrganizationRepository)
            ctx = OrganizationQueryContext(certificate_ctx=OrganizationCertificateQueryContext.default())

            org = org_repo.find(organization_id, ctx)
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
            ctx = OrganizationQueryContext(certificate_ctx=OrganizationCertificateQueryContext(id=id))
            repo = session.get_repository(OrganizationRepository)
            org = repo.find(organization_id, ctx)

            if org is None:
                raise RecordNotFoundError(organization_id)

            target = org.certificates[0]

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

    def delete_one(self, organization_id: UUID, id: UUID) -> Certificate:
        with self.db.get_db_session() as session:
            org_repo = session.get_repository(OrganizationRepository)
            if not org_repo.exists(organization_id):
                raise RecordNotFoundError(organization_id)

            ctx = CertificateQueryContext(client_ctx=CertificateClientQueryContext.default())
            cert_repo = session.get_repository(CertificateRepository)
            target = cert_repo.find(id, ctx)
            if target is None:
                raise RecordNotFoundError(id)

            valid_for_delete = self.validated_for_delete(target)
            if valid_for_delete is None:
                raise ForbidenOperationError()

            target.deleted_at = datetime.now()
            session.commit()

            return Certificate.from_entity(target)

    @staticmethod
    def validated_for_delete(cert: CertificateEntity) -> bool:
        valid = True
        if cert.clients:
            for c in cert.clients:
                if c.deleted_at is not None:
                    valid = False
                    break
        return valid

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
        update_list = [c.unique_key for c in update_certs]
        for key, value in current_certs_map.items():
            if key not in update_list:
                value.deleted_at = datetime.now()
                update_certs.append(value)

        return update_certs
