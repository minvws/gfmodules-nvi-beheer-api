import logging
from typing import List
from uuid import UUID

from app.db.db import Database
from app.db.models.client import ClientEntity
from app.db.repository.client import ClientRepository
from app.db.repository.organization import OrganizationRepository
from app.logging.events import Log
from app.models.oin import Oin
from app.models.ura import UraNumber
from app.services.exceptions import RecordNotFoundError
from app.services.organization import OrganizationService
from app.services.scopes import ScopeService

logger = logging.getLogger(__name__)


class ClientService:
    def __init__(
        self,
        db: Database,
        org_service: OrganizationService,
    ) -> None:
        self.db = db
        self.org_service = org_service

    def create_one(
        self,
        organization_id: UUID,
        oin: Oin,
        common_name: str,
        source_id: str | None = None,
        scopes: List[str] | None = None,
    ) -> ClientEntity:
        with self.db.get_db_session() as session:
            org_repo = session.get_repository(OrganizationRepository)
            org = org_repo.find_one(organization_id)
            if not org:
                raise RecordNotFoundError(f"Organization with id {organization_id} does not exist.")

            if scopes:
                OrganizationService.assert_scopes_granted(org, scopes)

            repo = session.get_repository(ClientRepository)
            client_scopes = ScopeService.make_client_scope_from_org(org, scopes or [])
            entity = ClientEntity(
                organization_id=organization_id,
                source_id=source_id,
                oin=oin,
                common_name=common_name,
                scopes=client_scopes,
            )
            Log.event(
                logger=logger,
                event=Log.CLIENT_ONBOARDED,
                message="Client onboarded",
                oin=oin,
                ura_number=org.register_id,
                source_identifier=source_id,
                scopes=scopes,
                approved_by="system",
            )
            return repo.add_one(entity)

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
        scopes: List[str] | None = None,
        include_deleted: bool = False,
    ) -> List[ClientEntity]:
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
        scopes: List[str] | None = None,
    ) -> ClientEntity:
        with self.db.get_db_session() as session:
            org_repo = session.get_repository(OrganizationRepository)
            org = org_repo.find_one_with_specific_client(organization_id, id)
            if not org:
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
            new_scopes = ScopeService.make_client_scope_from_org(org, scopes)
            client.scopes = new_scopes
            session.add(client)
            session.commit()

        return client

    def delete_one(self, id: UUID, organization_id: UUID) -> None:
        with self.db.get_db_session() as session:
            org_repo = session.get_repository(OrganizationRepository)
            client_repo = session.get_repository(ClientRepository)

            org = org_repo.find_one_with_specific_client(organization_id, id)
            if org is None:
                raise RecordNotFoundError(organization_id)

            client = org.clients[0] if org.clients else None
            if client is None:
                raise RecordNotFoundError(id)

            Log.event(
                logger=logger,
                event=Log.CLIENT_OFFBOARDED,
                message="Client offboarded",
                oin=client.oin,
                ura_number=org.register_id,
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
