from sqlalchemy import Column, ForeignKey, Integer, Table, Uuid

from app.db.models.base import Base

clients_scopes_association = Table(
    "clients_scopes",
    Base.metadata,
    Column("client_id", Uuid, ForeignKey("clients.id"), primary_key=True),
    Column("organization_id", Uuid, ForeignKey("organizations_scopes.organization_id"), primary_key=True),
    Column("scope_id", Integer, ForeignKey("organizations_scopes.scope_id"), primary_key=True),
)
