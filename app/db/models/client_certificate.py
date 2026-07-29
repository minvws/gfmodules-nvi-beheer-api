from sqlalchemy import Column, ForeignKey, Table, Uuid

from app.db.models.base import Base

clients_certificates_association = Table(
    "clients_certificates",
    Base.metadata,
    Column("client_id", Uuid, ForeignKey("clients.id"), primary_key=True),
    Column("certificate_id", Uuid, ForeignKey("certificates.id"), primary_key=True),
)
