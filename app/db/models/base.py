from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import TIMESTAMP, String, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class CommonColumns(Base):
    __abstract__ = True

    id: Mapped[UUID] = mapped_column("id", Uuid, primary_key=True, default=uuid4)
    scopes: Mapped[Optional[str]] = mapped_column("scopes", String)
    created_at: Mapped[datetime] = mapped_column("created_at", TIMESTAMP, server_default=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column("deleted_at", TIMESTAMP)

    def __repr__(self) -> str:
        props = ", ".join([f"{k}={self.__getattribute__(k)}" for k in self.__table__.columns.keys()])
        return f"<{self.__class__.__name__}=({props})>"
