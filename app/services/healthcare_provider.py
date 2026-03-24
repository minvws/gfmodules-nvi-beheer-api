from uuid import UUID

from fastapi import HTTPException

from app.db.db import Database
from app.db.models.healthcare_provider import HealthcareProvider
from app.db.repository.healthcare_service import HealthcareProvidersRepository


class HeatlhcareProviderService:
    def __init__(self, db: Database) -> None:
        self.db = db

    def get_one(self, id: UUID) -> HealthcareProvider:
        with self.db.get_db_session() as session:
            repository = session.get_repository(HealthcareProvidersRepository)
            provider = repository.get_one(id)

            if provider is None:
                raise HTTPException(status_code=404)

            return provider

    def add_one(self, data: HealthcareProvider) -> HealthcareProvider:
        with self.db.get_db_session() as session:
            repo = session.get_repository(HealthcareProvidersRepository)
            new_provider = repo.add_one(data)

            return new_provider

    def delete_one(self, id: UUID) -> None:
        with self.db.get_db_session() as session:
            repo = session.get_repository(HealthcareProvidersRepository)
            target = repo.get_one(id)
            if target is None:
                raise HTTPException(status_code=404)

            repo.delete_one(target)
