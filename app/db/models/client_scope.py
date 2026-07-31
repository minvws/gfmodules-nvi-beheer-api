from sqlalchemy import Column, ForeignKey, Table, Uuid

from app.db.models.base import Base

clients_scopes_association = Table(
    "clients_scopes",
    Base.metadata,
    Column("client_id", Uuid, ForeignKey("clients.id"), primary_key=True),
    Column("scope_id", Uuid, ForeignKey("scopes.id"), primary_key=True),
)
