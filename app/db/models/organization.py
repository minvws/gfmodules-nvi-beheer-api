from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Index, String, text
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.db.models.base import CommonColumns
from app.db.models.organization_scope import organizations_scopes_association
from app.db.types.ura_type import UraType
from app.models.ura import UraNumber

if TYPE_CHECKING:
    from app.db.models.certificate import CertificateEntity
    from app.db.models.client import ClientEntity
    from app.db.models.scope import ScopeEntity
    from app.db.models.source import SourceEntity


class OrganizationEntity(CommonColumns):
    __tablename__ = "organizations"
    __table_args__ = (
        Index(
            "uq_organizations_external_id_active",
            "external_id",
            unique=True,
            sqlite_where=text("deleted_at IS NULL"),
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )
    external_id: Mapped[UraNumber] = mapped_column("external_id", UraType)  # TODO check if this is unique
    name: Mapped[str] = mapped_column("name", String)

    clients: Mapped[list["ClientEntity"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan", lazy="raise"
    )
    certificates: Mapped[list["CertificateEntity"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan", lazy="raise"
    )
    scopes: Mapped[list["ScopeEntity"]] = relationship(secondary=organizations_scopes_association, lazy="raise")
    sources: Mapped[list["SourceEntity"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan", lazy="raise"
    )
