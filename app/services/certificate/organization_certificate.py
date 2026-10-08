from datetime import UTC, datetime
from uuid import UUID

from app.db.db import Database
from app.db.models.certificate import CertificateEntity
from app.db.repository.certificate import CertificateRepository
from app.db.repository.contexts.certificate_context import (
    CertificateClientQueryContext,
    CertificateQueryContext,
)
from app.db.repository.contexts.organization_context import (
    OrganizationCertificateQueryContext,
    OrganizationQueryContext,
)
from app.db.repository.organization import OrganizationRepository
from app.models.certificates import (
    Certificate,
    CertificateCreate,
    CertificateQueryParams,
    CertificateUpdate,
)
from app.services.exceptions import (
    ConflictError,
    EntityHasActiveMembersError,
    RecordNotFoundError,
)


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
        with self.db.get_db_session(commit=True) as session:
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

            session.flush()

            return Certificate.from_entity(new_cert)

    def update_one(self, id: UUID, organization_id: UUID, dto: CertificateUpdate) -> Certificate:
        with self.db.get_db_session(commit=True) as session:
            ctx = OrganizationQueryContext(
                id=organization_id, certificate_ctx=OrganizationCertificateQueryContext(id=id)
            )
            repo = session.get_repository(OrganizationRepository)
            org = repo.find(ctx)

            if org is None:
                raise RecordNotFoundError(organization_id)

            if not org.certificates:
                raise RecordNotFoundError(id)

            target = org.certificates[0]

            if target is None:
                raise RecordNotFoundError(id)

            if CertificateUpdate.from_entity(target) == dto:
                return Certificate.from_entity(target)

            if target.organization_identifier != dto.organization_identifier:
                target.organization_identifier = dto.organization_identifier

            if target.domain != target.domain:
                target.domain = target.domain

            session.flush()

            return Certificate.from_entity(target)

    def delete_one(self, organization_id: UUID, id: UUID) -> Certificate:
        with self.db.get_db_session(commit=True) as session:
            org_repo = session.get_repository(OrganizationRepository)
            if not org_repo.exists(organization_id):
                raise RecordNotFoundError(organization_id)

            ctx = CertificateQueryContext(
                id=id, organization_id=organization_id, client_ctx=CertificateClientQueryContext.default()
            )
            cert_repo = session.get_repository(CertificateRepository)
            target = cert_repo.find(ctx)
            if target is None:
                raise RecordNotFoundError(id)

            active_memebers = self.validated_for_delete(target)
            if active_memebers is not None:
                raise EntityHasActiveMembersError("Certificate", active_memebers, id)

            target.deleted_at = datetime.now(UTC)
            session.flush()

            return Certificate.from_entity(target)

    @staticmethod
    def validated_for_delete(cert: CertificateEntity) -> str | None:
        if any(c.deleted_at is None for c in cert.clients):
            return "Clients"

        return None
