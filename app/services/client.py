import logging
from uuid import UUID

from app.db.db import Database
from app.db.models.client import ClientEntity
from app.db.repository.client import ClientRepository
from app.db.repository.organization import OrganizationRepository
from app.logging.events import Log
from app.models.client import Client, ClientCreate
from app.models.oin import Oin
from app.models.ura import UraNumber
from app.services import scopes
from app.services.certificate import ClientCertificateService
from app.services.exceptions import RecordNotFoundError
from app.services.organization import OrganizationService
from app.services.scopes import ScopeService
from app.services.source import SourceService

logger = logging.getLogger(__name__)


class ClientService:
    def __init__(
        self,
        db: Database,
        org_service: OrganizationService,
    ) -> None:
        self.db = db
        self.org_service = org_service

    def create_one(self, organization_id: UUID, dto: ClientCreate) -> Client:
        with self.db.get_db_session() as session:
            org_repo = session.get_repository(OrganizationRepository)
            org = org_repo.find_one(organization_id)
            if not org:
                raise RecordNotFoundError(f"Organization with id {organization_id} does not exist.")

            target = ClientEntity(name=dto.name, description=dto.description, organization_id=organization_id)
            if dto.scopes:
                ScopeService.assert_scopes_granted(org, dto.sanatized_scopes or [])
                target_scope = ScopeService.make_client_scope_from_org(org, target, dto.sanatized_scopes or [])
                target.scopes = target_scope

            if dto.certificates:
                client_certs = ClientCertificateService.get_client_certs_from_org(org, dto.certificates)
                target.certificates = client_certs

            if dto.sources:
                client_sources = SourceService.get_client_sources_from_org(org, dto.sources)
                target.sources = client_sources

            client_repo = session.get_repository(ClientRepository)
            new_client = client_repo.add_one(target)
            Log.event(
                logger=logger,
                event=Log.CLIENT_ONBOARDED,
                message="Client onboarded",
                # oin=oin,
                ura_number=org.external_id,
                # source_identifier=source_id,
                scopes=scopes,
                approved_by="system",
            )

            return Client.from_entity(new_client)

    def get_one(self, id: UUID, organization_id: UUID) -> ClientEntity | None:
        with self.db.get_db_session() as session:
            repo = session.get_repository(ClientRepository)
            return repo.find_one(organization_id, id)

    def get_many(
        self,
        organization_id: UUID,
        oin: Oin | None = None,
        common_name: str | None = None,
        source_id: str | None = None,
        scopes: list[str] | None = None,
        include_deleted: bool = False,
    ) -> list[ClientEntity]:
        with self.db.get_db_session() as session:
            repo = session.get_repository(ClientRepository)
            return list(
                repo.find_many(
                    organization_id=organization_id,
                    oin=oin,
                    common_name=common_name,
                    source_id=source_id,
                    scopes=scopes,
                    include_deleted=include_deleted,
                )
            )

    def update_one(
        self,
        id: UUID,
        organization_id: UUID,
        common_name: str,
        oin: Oin,
        source_id: str | None = None,
        scopes: list[str] | None = None,
    ) -> ClientEntity:
        with self.db.get_db_session() as session:
            org_repo = session.get_repository(OrganizationRepository)
            org = org_repo.find_one_with_specific_client(organization_id, id)
            if org is None:
                raise RecordNotFoundError(organization_id)
            client = org.clients[0] if org.clients else None
            if client is None:
                raise RecordNotFoundError(id)

            client.common_name = common_name
            client.oin = oin
            client.source_id = source_id
            if not scopes:
                client.scopes = []

                session.add(client)
                session.commit()
                return client

            OrganizationService.assert_scopes_granted(org, scopes)
            new_scopes = ScopeService.make_client_scope_from_org(org, client, scopes)
            client.scopes = new_scopes
            session.add(client)
            session.commit()

            return client

    def delete_one(self, id: UUID, organization_id: UUID) -> None:
        with self.db.get_db_session() as session:
            org_repo = session.get_repository(OrganizationRepository)
            client_repo = session.get_repository(ClientRepository)

            if not org_repo.exists(organization_id):
                raise RecordNotFoundError(organization_id)

            client = client_repo.find_one(organization_id, id)
            if client is None:
                raise RecordNotFoundError(id)

            Log.event(
                logger=logger,
                event=Log.CLIENT_OFFBOARDED,
                message="Client offboarded",
                oin=client.oin,
                ura_number=client.organization.register_id,
                deactivated_by="system",
                reason="Deleted by system",
            )
            return client_repo.delete_one(id)

    def resolve(
        self,
        oin: Oin,
        common_name: str,
        org_ura: UraNumber,
    ) -> ClientEntity | None:
        with self.db.get_db_session() as session:
            repo = session.get_repository(ClientRepository)
            return repo.get_by_credentials(common_name=common_name, oin=oin, org_ura=org_ura)
