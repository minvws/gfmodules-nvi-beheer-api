from datetime import datetime

from sqlalchemy import TIMESTAMP, Enum, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base
from app.models.scopes import AuthorizationScope


class ScopeEntity(Base):
    __tablename__ = "scopes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[AuthorizationScope] = mapped_column(Enum(AuthorizationScope))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
