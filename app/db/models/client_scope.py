from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, Integer, Table, Uuid

from app.db.models.base import Base

clients_scopes_association = Table(
    "clients_scopes",
    Base.metadata,
    Column("client_id", Uuid, ForeignKey("admin.clients.id"), primary_key=True),
    Column("organization_id", Uuid, primary_key=True),
    Column("scope_id", Integer, primary_key=True),
    ForeignKeyConstraint(
        columns=["organization_id", "scope_id"],
        refcolumns=["admin.organizations_scopes.organization_id", "admin.organizations_scopes.scope_id"],
        name="fk_clients_scopes_scopes",
    ),
    schema="admin",
)
