from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.models.base import CommonColumns
from app.db.models.client_source import clients_sources_association

if TYPE_CHECKING:
    from app.db.models.client import ClientEntity
    from app.db.models.organization import OrganizationEntity


class SourceEntity(CommonColumns):
    __tablename__ = "sources"
    __table_args__ = (
        Index(
            "uq_sources_source_id_active",
            "source_id",
            unique=True,
            sqlite_where=text("deleted_at IS NULL"),
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    source_id: Mapped[str] = mapped_column("source_id", String)
    name: Mapped[str] = mapped_column("name", String)
    organization_id: Mapped[UUID] = mapped_column("organization_id", Uuid, ForeignKey("organizations.id"))

    organization: Mapped["OrganizationEntity"] = relationship(back_populates="sources")
    clients: Mapped[list["ClientEntity"]] = relationship(
        back_populates="sources", secondary=clients_sources_association
    )
