from sqlalchemy import Column, ForeignKey, Table
from sqlalchemy.types import Uuid

from app.db.models.base import Base

clients_sources_association = Table(
    "clients_sources",
    Base.metadata,
    Column("client_id", Uuid, ForeignKey("clients.id")),
    Column("source_id", Uuid, ForeignKey("sources.id")),
)
