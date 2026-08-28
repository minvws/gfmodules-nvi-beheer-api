from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.models.base import CommonColumns
from app.db.models.client import ClientEntity
from app.db.models.client_certificate import clients_certificates_association
from app.db.types.oin_type import OinType
from app.models.oin import Oin

if TYPE_CHECKING:
    from app.db.models.organization import OrganizationEntity


class CertificateEntity(CommonColumns):
    __tablename__ = "certificates"
    __table_args__ = (
        Index(
            "uq_organization_id_organization_identifier_domain",
            "organization_id",
            "organization_identifier",
            "domain",
            unique=True,
        ),
    )

    organization_identifier: Mapped[Oin] = mapped_column("organization_identifier", OinType)
    domain: Mapped[str] = mapped_column("domain", String)
    organization_id: Mapped[UUID] = mapped_column("organization_id", Uuid, ForeignKey("organizations.id"))

    organization: Mapped["OrganizationEntity"] = relationship(back_populates="certificates", lazy="raise")
    clients: Mapped[Optional[list["ClientEntity"]]] = relationship(
        back_populates="certificates", secondary=clients_certificates_association, lazy="raise"
    )

    @property
    def unique_key(self) -> str:
        return f"{self.organization_id}-{self.organization_identifier}-{self.domain}"
