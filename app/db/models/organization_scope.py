from sqlalchemy import Column, ForeignKey, Table

from app.db.models.base import Base

organizations_scopes_association = Table(
    "organizations_scopes",
    Base.metadata,
    Column("organization_id", ForeignKey("organizations.id")),
    Column("scope_id", ForeignKey("scopes.id")),
)
