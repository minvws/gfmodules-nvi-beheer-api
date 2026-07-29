from typing import NamedTuple

from sqlalchemy import select, tuple_
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
