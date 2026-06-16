from __future__ import annotations

from typing import TYPE_CHECKING, List

from sqlalchemy import Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import CommonColumns

if TYPE_CHECKING:
    from app.db.models.client import ClientEntity


class OrganizationEntity(CommonColumns):
    __tablename__ = "organizations"
    __table_args__ = (
        Index(
            "uq_organizations_register_id_active",
            "register_id",
            unique=True,
            sqlite_where=text("deleted_at IS NULL"),
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    register_id: Mapped[str] = mapped_column(
        "register_id", String
    )  # ID of the organization: {OIN} for PRS - {URA} for NVI
    name: Mapped[str] = mapped_column("name", String)

    clients: Mapped[List["ClientEntity"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan", lazy="raise"
    )
