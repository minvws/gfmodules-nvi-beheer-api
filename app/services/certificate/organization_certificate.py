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

            ctx = CertificateQueryContext(
                organization_id=organization_id, **params.model_dump(exclude={"include_deleted"})
            )
            cert_repo = session.get_repository(CertificateRepository)
            certs = cert_repo.find_many(ctx, params.include_deleted)

            return [Certificate.from_entity(c) for c in certs]

    def create_one(self, organization_id: UUID, dto: CertificateCreate) -> Certificate:
        with self.db.get_db_session() as session:
            org_repo = session.get_repository(OrganizationRepository)
            ctx = OrganizationQueryContext(
                id=organization_id, certificate_ctx=OrganizationCertificateQueryContext.default()
            )

            org = org_repo.find(ctx)
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
            ctx = OrganizationQueryContext(
                id=organization_id, certificate_ctx=OrganizationCertificateQueryContext(id=id)
            )
            repo = session.get_repository(OrganizationRepository)
            org = repo.find(ctx)

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

            ctx = CertificateQueryContext(id=id, client_ctx=CertificateClientQueryContext.default())
            cert_repo = session.get_repository(CertificateRepository)
            target = cert_repo.find(ctx)
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
        org: OrganizationEntity, target: list[CertificateCreate | CertificateUpdate]
    ) -> list[CertificateEntity]:
        # handle new certs
        results = [CertificateEntity(**c.model_dump()) for c in target if isinstance(c, CertificateCreate)]
        updated_ids: list[UUID] = []

        current_cert_map = {c.id: c for c in org.certificates}

        for cert in target:
            if not isinstance(cert, CertificateUpdate):
                continue

            current_cert = current_cert_map.get(cert.id)
            if current_cert is None:
                raise ForbidenOperationError(
                    f"id {cert.id} is not allowed to be added."
                )  # TODO: more descriptive error
            current_cert.organization_identifier = cert.organization_identifier
            current_cert.domain = cert.domain

            results.append(current_cert)
            updated_ids.append(current_cert.id)

        # handle soft delete
        for key, value in current_cert_map.items():
            if key not in updated_ids:
                value.deleted_at = datetime.now()
                results.append(value)

        return results
