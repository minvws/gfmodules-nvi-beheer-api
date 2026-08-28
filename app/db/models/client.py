from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.models.base import CommonColumns
from app.db.models.client_certificate import clients_certificates_association
from app.db.models.client_scope import clients_scopes_association
from app.db.models.client_source import clients_sources_association

if TYPE_CHECKING:
    from app.db.models.certificate import CertificateEntity
    from app.db.models.organization import OrganizationEntity
    from app.db.models.scope import ScopeEntity
    from app.db.models.source import SourceEntity


class ClientEntity(CommonColumns):
    __tablename__ = "clients"

    name: Mapped[str] = mapped_column("name", String)
    description: Mapped[str | None] = mapped_column("description", String)
    organization_id: Mapped[UUID] = mapped_column("organization_id", Uuid, ForeignKey("organizations.id"))

    organization: Mapped["OrganizationEntity"] = relationship(back_populates="clients", lazy="raise")
    scopes: Mapped[Optional[list["ScopeEntity"]]] = relationship(
        secondary=clients_scopes_association,
        primaryjoin="and_(ClientEntity.id == clients_scopes.c.client_id, ClientEntity.organization_id == clients_scopes.c.organization_id)",
        secondaryjoin="ScopeEntity.id == clients_scopes.c.scope_id",
        lazy="raise",
    )
    certificates: Mapped[Optional[list["CertificateEntity"]]] = relationship(
        back_populates="clients", secondary=clients_certificates_association, lazy="raise"
    )
    sources: Mapped[Optional[list["SourceEntity"]]] = relationship(
        back_populates="clients", secondary=clients_sources_association, lazy="raise"
    )
