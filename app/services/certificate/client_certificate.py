from uuid import UUID

from app import utils
from app.db.db import Database
from app.db.models.certificate import CertificateEntity
from app.db.models.organization import OrganizationEntity
from app.db.repository.organization import OrganizationRepository
from app.models.certificates import Certificate, CertificateCreate, CertificateUpdate
from app.services.exceptions import ConflictError, ForbidenOperationError, RecordNotFoundError


class ClientCertificateService:
    def __init__(self, database: Database) -> None:
        self.db = database

    def get_one(self, organization_id: UUID, client_id: UUID, id: UUID) -> Certificate:
        with self.db.get_db_session() as session:
            repo = session.get_repository(OrganizationRepository)
            org = repo.find(id=organization_id, client_id=client_id, certificate_id=id)
            if org is None:
                raise RecordNotFoundError(organization_id)

            if not org.clients:
                raise RecordNotFoundError(client_id)

            client = org.clients[0]
            if not client.certificates:
                raise RecordNotFoundError(id)

            target_cert = client.certificates[0]
            assert len(client.certificates) == 1
            return Certificate.from_entity(target_cert)

    def assign_one(self, organization_id: UUID, client_id: UUID, id: UUID) -> Certificate:
        with self.db.get_db_session() as session:
            repo = session.get_repository(OrganizationRepository)
            org = repo.find(id=organization_id, client_id=client_id, certificate_id=id)

            if org is None:
                raise RecordNotFoundError(organization_id)

            if not org.clients:
                raise RecordNotFoundError(client_id)

            if not org.certificates:
                raise RecordNotFoundError(id)

            target_cert = org.certificates[0]
            client = org.clients[0]
            if not client.certificates:
                client.certificates = [target_cert]
                session.commit()
                return Certificate.from_entity(target_cert)

            # TODO: guarantee one so no need for this iterable
            if any(c.id == id for c in client.certificates):
                raise ConflictError(f"Certificate {id} already assigned to client {client_id}")

            client.certificates.append(target_cert)
            session.commit()

            return Certificate.from_entity(target_cert)

    @staticmethod
    def get_client_certs_from_org(
        org: OrganizationEntity, certs: list[CertificateCreate] | list[CertificateUpdate]
    ) -> list[CertificateEntity]:
        org_cert_keys = [c.unique_key for c in org.certificates] if org.certificates else []
        client_cert_keys = [c.make_unique_key(org.id) for c in certs]
        if not utils.is_subset(org_cert_keys, client_cert_keys):
            raise ForbidenOperationError("Client certs are not allowed to be assigned")

        return [c for c in org.certificates if c.unique_key in client_cert_keys] if org.certificates else []
