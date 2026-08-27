from typing import NamedTuple, Sequence
from uuid import UUID

from sqlalchemy import and_, select, tuple_
from sqlalchemy.exc import SQLAlchemyError

from app.db.decorator import repository
from app.db.models.certificate import CertificateEntity
from app.db.repository.base import RepositoryBase


class CertificateIndexLookup(NamedTuple):
    organization_identifier: str
    domain: str


@repository(CertificateEntity)
class CertificateRepository(RepositoryBase):
    def add_one(self, data: CertificateEntity) -> CertificateEntity:
        try:
            self.db_session.add(data)
            self.db_session.commit()
            self.db_session.session.refresh(data)
            return data
        except SQLAlchemyError:
            self.db_session.rollback()
            raise

    def exists(self, data: CertificateIndexLookup | list[CertificateIndexLookup]) -> bool:
        stmt = select(
            select(CertificateEntity)
            .where(tuple_(CertificateEntity.organization_identifier, CertificateEntity.domain).in_(data))
            .exists()
        )

        return bool(self.db_session.execute(stmt).scalar())

    def find_one(self, id: UUID, organizatoin_id: UUID) -> CertificateEntity | None:
        stmt = select(CertificateEntity).where(
            and_(
                CertificateEntity.id == id,
                CertificateEntity.organization_id == organizatoin_id,
                CertificateEntity.deleted_at.is_(None),
            )
        )

        return self.db_session.execute(stmt).scalar()

    def find_many(
        self,
        organization_id: UUID,
        organization_identifier: str | None = None,
        domain: str | None = None,
        include_deleted: bool = False,
    ) -> Sequence[CertificateEntity]:
        conditions = [(CertificateEntity.organization_id == organization_id)]
        if organization_identifier:
            conditions.append(CertificateEntity.organization_identifier == organization_identifier)

        if domain:
            conditions.append(CertificateEntity.domain == domain)

        if include_deleted:
            conditions.append(CertificateEntity.deleted_at.is_not(None))

        stmt = select(CertificateEntity).where(and_(*conditions))

        return self.db_session.execute(stmt).scalars().all()
