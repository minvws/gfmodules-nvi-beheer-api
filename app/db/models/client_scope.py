from sqlalchemy import Column, ForeignKey, Table

from app.db.models.base import Base

clients_scopes_association = Table(
    "clients_scopes",
    Base.metadata,
    Column("client_id", ForeignKey("clients.id")),
    Column("scope_id", ForeignKey("scopes.id")),
)
