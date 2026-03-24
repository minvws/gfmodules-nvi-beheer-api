from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.db.decorator import repository
from app.db.models.healthcare_provider import HealthcareProvider
from app.db.repository.base import RepositoryBase


@repository(HealthcareProvider)
class HealthcareProvidersRepository(RepositoryBase):
    def add_one(self, data: HealthcareProvider) -> HealthcareProvider:
        try:
            self.db_session.add(data)
            self.db_session.commit()
            return data
        except SQLAlchemyError as e:
            self.db_session.rollback()
            raise e

    def delete_one(self, data: HealthcareProvider) -> None:
        try:
            self.db_session.delete(data)
            self.db_session.commit()
        except SQLAlchemyError as e:
            self.db_session.rollback()
            raise e

    def get_one(self, id: UUID) -> HealthcareProvider | None:
        stmt = select(HealthcareProvider).where(HealthcareProvider.id == id)
        results = self.db_session.session.execute(stmt).scalar()
        return results
