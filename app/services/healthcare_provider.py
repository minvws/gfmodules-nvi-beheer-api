from datetime import datetime
from uuid import UUID

from app.db.db import Database
from app.db.models.healthcare_provider import HealthcareProviderEntity
from app.db.repository.healthcare_provider import HealthcareProvidersRepository


class HeatlhcareProviderService:
    def __init__(self, db: Database) -> None:
        self.db = db

    def get_one(self, id: UUID) -> HealthcareProviderEntity | None:
        with self.db.get_db_session() as session:
            repository = session.get_repository(HealthcareProvidersRepository)
            provider = repository.get_one(id)

            return provider

    def create_one(
        self,
        ura_number: str,
        is_source: bool,
        is_viewer: bool,
        oin: str,
        common_name: str,
        status: str,
        source_id: str | None = None,
    ) -> HealthcareProviderEntity:
        with self.db.get_db_session() as session:
            repo = session.get_repository(HealthcareProvidersRepository)
            target = HealthcareProviderEntity(
                ura_number=ura_number,
                source_id=source_id,
                is_viewer=is_viewer,
                is_source=is_source,
                oin=oin,
                common_name=common_name,
                status=status,
            )
            new_provider = repo.add_one(target)

            return new_provider

    def delete_one(self, id: UUID) -> HealthcareProviderEntity | None:
        with self.db.get_db_session() as session:
            repo = session.get_repository(HealthcareProvidersRepository)
            deleted_data = repo.update(id, deleted_at=datetime.now())

            return deleted_data

    def update_one(self, id: UUID, **kwargs: object) -> HealthcareProviderEntity | None:
        with self.db.get_db_session() as session:
            repo = session.get_repository(HealthcareProvidersRepository)
            updated_data = repo.update(id, **kwargs)

            return updated_data
