from uuid import UUID

from app import utils
from app.db.db import Database
from app.db.models.certificate import CertificateEntity
from app.db.models.organization import OrganizationEntity
from app.db.repository.client import ClientRepository
from app.db.repository.organization import OrganizationRepository
from app.db.repository.query_builder.context.client_context import ClientCertificateQueryContext, ClientQueryContext
from app.db.repository.query_builder.context.organization_context import (
    OrganizationCertificateQueryContext,
    OrganizationClientQueryContext,
    OrganizationQueryContext,
)
from app.models.certificates import Certificate, CertificateCreate, CertificateQueryParams, CertificateUpdate
from app.services.exceptions import ConflictError, ForbidenOperationError, RecordNotFoundError


class ClientCertificateService:
    def __init__(self, database: Database) -> None:
        self.db = database

    def get_one(self, organization_id: UUID, client_id: UUID, id: UUID) -> Certificate:
        with self.db.get_db_session() as session:
            org_repo = session.get_repository(OrganizationRepository)
            if not org_repo.exists(organization_id):
                raise RecordNotFoundError(organization_id)

            client_repo = session.get_repository(ClientRepository)
            ctx = ClientQueryContext(certificate_ctx=ClientCertificateQueryContext(id=id))

            client = client_repo.find(client_id, organization_id, ctx)
            if client is None:
                raise RecordNotFoundError(client_id)

            if not client.certificates:
                raise RecordNotFoundError(id)

            cert = client.certificates[0]

            return Certificate.from_entity(cert)

    def get_many(self, organization_id: UUID, client_id: UUID, params: CertificateQueryParams) -> list[Certificate]:
        with self.db.get_db_session() as session:
            org_repo = session.get_repository(OrganizationRepository)
            if not org_repo.exists(organization_id):
                raise RecordNotFoundError(organization_id)

            cert_ctx = ClientCertificateQueryContext(
                domain=params.domain, organization_identifier=params.organization_identifier
            )
            ctx = ClientQueryContext(certificate_ctx=cert_ctx)

            client_repo = session.get_repository(ClientRepository)
            client = client_repo.find(client_id, organization_id, ctx)
            if client is None:
                raise RecordNotFoundError(client_id)

            return [Certificate.from_entity(c) for c in client.certificates]

    def assign_one(self, organization_id: UUID, client_id: UUID, id: UUID) -> Certificate:
        with self.db.get_db_session() as session:
            repo = session.get_repository(OrganizationRepository)
            cert_ctx = OrganizationCertificateQueryContext(id=id)
            ctx = OrganizationQueryContext(
                client_ctx=OrganizationClientQueryContext(id=client_id, certificate_ctx=cert_ctx),
                certificate_ctx=cert_ctx,
            )
            org = repo.find(id=organization_id, ctx=ctx)

            if org is None:
                raise RecordNotFoundError(organization_id)

            if not org.clients:
                raise RecordNotFoundError(client_id)

            if not org.certificates:
                raise RecordNotFoundError(id)

            target_cert = org.certificates[0]
            client = org.clients[0]

            if client.certificates:
                raise ConflictError(f"Certificate {id} already assigned to client {client_id}")

            client.certificates.append(target_cert)
            session.commit()
            return Certificate.from_entity(target_cert)

    def unassign_one(self, organization_id: UUID, client_id: UUID, id: UUID) -> Certificate:
        with self.db.get_db_session() as session:
            org_repo = session.get_repository(OrganizationRepository)

            cert_ctx = OrganizationCertificateQueryContext(id=id)
            ctx = OrganizationQueryContext(
                certificate_ctx=cert_ctx,
                client_ctx=OrganizationClientQueryContext(id=client_id, certificate_ctx=cert_ctx),
            )
            org = org_repo.find(id=organization_id, ctx=ctx)
            if org is None:
                raise RecordNotFoundError(organization_id)

            if not org.clients:
                raise RecordNotFoundError(client_id)

            if not org.certificates:
                raise RecordNotFoundError(id)

            client = org.clients[0]
            if not client.certificates:
                raise RecordNotFoundError(f"Client {client_id} has not certificate {id} assigned")

            target = client.certificates.pop(0)
            session.commit()

            return Certificate.from_entity(target)

    @staticmethod
    def get_client_certs_from_org(
        org: OrganizationEntity, certs: list[CertificateCreate] | list[CertificateUpdate]
    ) -> list[CertificateEntity]:
        org_cert_keys = [c.unique_key for c in org.certificates] if org.certificates else []
        client_cert_keys = [c.make_unique_key(org.id) for c in certs]
        if not utils.is_subset(org_cert_keys, client_cert_keys):
            raise ForbidenOperationError("Client certs are not allowed to be assigned")

        return [c for c in org.certificates if c.unique_key in client_cert_keys] if org.certificates else []
