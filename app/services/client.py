from datetime import datetime
from typing import List
from uuid import UUID

from app.db.db import Database
from app.db.models.client import ClientEntity
from app.db.repository.client import ClientRepository
from app.models.oin import Oin
from app.models.ura import UraNumber
from app.services.organization import OrganizationService


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
        scopes: str | None = None,
    ) -> ClientEntity:
        with self.db.get_db_session() as session:
            self.org_service.assert_scopes_granted(organization_id, scopes)
            repo = session.get_repository(ClientRepository)
            entity = ClientEntity(
                organization_id=organization_id,
                source_id=source_id,
                oin=oin,
                common_name=common_name,
                scopes=scopes,
            )
            return repo.add_one(entity)

    def get_one(self, id: UUID, organization_id: UUID) -> ClientEntity | None:
        with self.db.get_db_session() as session:
            repo = session.get_repository(ClientRepository)
            return repo.get_one(organization_id, id)

    def get_many(
        self,
        organization_id: UUID,
        oin: Oin | None = None,
        common_name: str | None = None,
        source_id: str | None = None,
        scopes: str | None = None,
        include_deleted: bool = False,
    ) -> List[ClientEntity]:
        with self.db.get_db_session() as session:
            repo = session.get_repository(ClientRepository)
            return list(
                repo.get_many(
                    organization_id=organization_id,
                    oin=oin,
                    common_name=common_name,
                    source_id=source_id,
                    scopes=scopes,
                    include_deleted=include_deleted,
                )
            )

    def update_one(self, id: UUID, organization_id: UUID, **kwargs: object) -> ClientEntity | None:
        with self.db.get_db_session() as session:
            repo = session.get_repository(ClientRepository)
            if not repo.exists(organization_id, id):
                return None
            if "scopes" in kwargs:
                self.org_service.assert_scopes_granted(organization_id, kwargs["scopes"])  # type: ignore[arg-type]
            return repo.update(organization_id, id, **kwargs)

    def delete_one(self, id: UUID, organization_id: UUID) -> ClientEntity | None:
        with self.db.get_db_session() as session:
            repo = session.get_repository(ClientRepository)
            if not repo.exists(organization_id, id):
                return None
            return repo.update(organization_id, id, deleted_at=datetime.now())

    def resolve(
        self,
        oin: Oin,
        common_name: str,
        org_ura: UraNumber,
    ) -> ClientEntity | None:
        with self.db.get_db_session() as session:
            repo = session.get_repository(ClientRepository)
            return repo.get_by_credentials(common_name=common_name, oin=oin, org_ura=org_ura)
