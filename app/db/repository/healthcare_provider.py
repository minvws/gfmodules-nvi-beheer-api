from uuid import UUID

from sqlalchemy import and_, select, update
from sqlalchemy.exc import SQLAlchemyError

from app.db.decorator import repository
from app.db.models.healthcare_provider import HealthcareProviderEntity
from app.db.repository.base import RepositoryBase


@repository(HealthcareProviderEntity)
class HealthcareProvidersRepository(RepositoryBase):
    def add_one(self, data: HealthcareProviderEntity) -> HealthcareProviderEntity:
        try:
            self.db_session.add(data)
            self.db_session.commit()
            return data
        except SQLAlchemyError as e:
            self.db_session.rollback()
            raise e

    def get_one(self, id: UUID) -> HealthcareProviderEntity | None:
        stmt = select(HealthcareProviderEntity).where(
            and_(
                HealthcareProviderEntity.id == id,
                HealthcareProviderEntity.deleted_at.is_(None),
            )
        )
        results = self.db_session.session.execute(stmt).scalar()
        return results

    def update(self, id: UUID, **kwargs: object) -> HealthcareProviderEntity | None:
        try:
            target = {k: kwargs[k] for k in HealthcareProviderEntity.__table__.columns.keys() if k in kwargs}
            if not target:
                return None

            stmt = (
                update(HealthcareProviderEntity)
                .where(
                    and_(
                        HealthcareProviderEntity.id == id,
                        HealthcareProviderEntity.deleted_at.is_(None),
                    )
                )
                .values(target)
                .returning(HealthcareProviderEntity)
            )

            results = self.db_session.session.execute(stmt).scalar_one_or_none()
            self.db_session.commit()
            return results
        except SQLAlchemyError as e:
            self.db_session.rollback()
            raise e
