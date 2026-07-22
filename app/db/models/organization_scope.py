from sqlalchemy import Column, ForeignKey, Integer, Table
from sqlalchemy.types import Uuid

from app.db.models.base import Base

organizations_scopes_association = Table(
    "organizations_scopes",
    Base.metadata,
    Column("organization_id", Uuid, ForeignKey("organizations.id"), primary_key=True),
    Column("scope_id", Integer, ForeignKey("scopes.id"), primary_key=True),
)
