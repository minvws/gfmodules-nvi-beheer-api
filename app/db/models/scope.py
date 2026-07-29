from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import TIMESTAMP, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base
from app.db.models.client_scope import clients_scopes_association
from app.db.models.organization_scope import organizations_scopes_association

if TYPE_CHECKING:
    from app.db.models.client import ClientEntity
    from app.db.models.organization import OrganizationEntity


class ScopeEntity(Base):
    __tablename__ = "scopes"

    id: Mapped[int] = mapped_column("id", Integer, primary_key=True)
    name: Mapped[str] = mapped_column("name", String)
    created_at: Mapped[datetime] = mapped_column("created_at", TIMESTAMP, server_default=func.now())

    organizations: Mapped["OrganizationEntity"] = relationship(secondary=organizations_scopes_association)
    clients: Mapped["ClientEntity"] = relationship(
        secondary=clients_scopes_association,
        primaryjoin="ScopeEntity.id == clients_scopes.c.scope_id",
        secondaryjoin="ClientEntity.id == clients_scopes.c.client_id",
    )
