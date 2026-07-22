from app import utils
from app.db.db import Database
from app.db.models.certificate import CertificateEntity
from app.db.models.organization import OrganizationEntity
from app.models.certificates import CertificateCreate
from app.services.exceptions import ForbidenOperationError


class ClientCertificateService:
    def __init__(self, database: Database) -> None:
        self.db = database

    @staticmethod
    def get_client_certs_from_org(org: OrganizationEntity, certs: list[CertificateCreate]) -> list[CertificateEntity]:
        org_cert_keys = [c.unique_key for c in org.certificates] if org.certificates else []
        client_cert_keys = [c.make_unique_key(org.id) for c in certs]
        if not utils.is_subset(org_cert_keys, client_cert_keys):
            raise ForbidenOperationError("Client certs are not allowed to be assigned")

        return [c for c in org.certificates if c.unique_key in client_cert_keys] if org.certificates else []
