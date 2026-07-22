from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import CommonColumns
from app.db.models.client_scope import clients_scopes_association
from app.db.models.organization_scope import organizations_scopes_association

if TYPE_CHECKING:
    from app.db.models.client import ClientEntity
    from app.db.models.organization import OrganizationEntity


# TODO: check the modified_at column
class ScopeEntity(CommonColumns):
    __tablename__ = "scopes"

    name: Mapped[str] = mapped_column("name", String)

    # TODO:: Maybe we dont need these
    organizations: Mapped["OrganizationEntity"] = relationship(
        back_populates="scopes", secondary=organizations_scopes_association
    )
    clients: Mapped[Optional[List["ClientEntity"]]] = relationship(
        back_populates="scopes", lazy="raise", secondary=clients_scopes_association
    )
