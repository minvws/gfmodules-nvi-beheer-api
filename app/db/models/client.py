from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.models.base import CommonColumns
from app.db.types.oin_type import OinType
from app.models.oin import Oin

if TYPE_CHECKING:
    from app.db.models.organization import OrganizationEntity


class ClientEntity(CommonColumns):
    __tablename__ = "clients"
    __table_args__ = (
        Index(
            "uq_clients_org_oin_cn_active",
            "organization_id",
            "oin",
            "common_name",
            unique=True,
            sqlite_where=text("deleted_at IS NULL"),
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    organization_id: Mapped[UUID] = mapped_column("organization_id", Uuid, ForeignKey("organizations.id"))

    oin: Mapped[Oin] = mapped_column("oin", OinType)
    common_name: Mapped[str] = mapped_column("common_name", String)
    source_id: Mapped[str | None] = mapped_column("source_id", String, nullable=True)

    organization: Mapped["OrganizationEntity"] = relationship(back_populates="clients", lazy="raise")
