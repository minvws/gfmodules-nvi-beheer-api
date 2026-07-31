from typing import TYPE_CHECKING, Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import CommonColumns
from app.db.models.client_scope import clients_scopes_association
from app.db.models.organization_scope import organizations_scopes_association

if TYPE_CHECKING:
    from app.db.models.client import ClientEntity
    from app.db.models.organization import OrganizationEntity


# TODO: check the modified_at column
# TODO make type WriteOnly


class ScopeEntity(CommonColumns):
    __tablename__ = "scopes"

    name: Mapped[str] = mapped_column("name", String)

    organizations: Mapped[list["OrganizationEntity"]] = relationship(
        back_populates="scopes",
        secondary=organizations_scopes_association,
        uselist=True,
    )
    clients: Mapped[Optional[list["ClientEntity"]]] = relationship(
        back_populates="scopes",
        lazy="raise",
        secondary=clients_scopes_association,
    )
