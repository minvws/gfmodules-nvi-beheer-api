from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Index, String, text
from sqlalchemy.ext.hybrid import hybrid_property
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
    from app.db.models.client import ClientEntity
    from app.db.models.scope import ScopeEntity


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

    register_id: Mapped[UraNumber] = mapped_column("register_id", UraType)
    name: Mapped[str] = mapped_column("name", String)

    clients: Mapped[Optional[list["ClientEntity"]]] = relationship(back_populates="organization", lazy="raise")
    scopes: Mapped[list["ScopeEntity"]] = relationship(
        secondary=organizations_scopes_association,
        back_populates="organizations",
    )

    @hybrid_property
    def org_scopes(self) -> list[str] | None:
        return [s.name for s in self.scopes] if self.scopes else None
