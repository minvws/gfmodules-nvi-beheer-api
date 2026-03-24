from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.models.base import Base


class HealthcareProvider(Base):
    __tablename__ = "healthcare_providers"
    __table_args__ = (
        UniqueConstraint("ura_number", "source_id", name="ura_number_source_idx"),
        UniqueConstraint("ura_number", "oin_certificate", name="ura_number_oin_certificate_idx"),
    )

    id: Mapped[UUID] = mapped_column("id", Uuid, primary_key=True, default=uuid4)
    ura_number: Mapped[str] = mapped_column("ura_number", String)
    source_id: Mapped[Optional[str]] = mapped_column("source_id", String)
    is_source: Mapped[bool] = mapped_column("is_source", Boolean)
    is_viewer: Mapped[bool] = mapped_column("is_viewer", Boolean)
    oin_certificate: Mapped[str] = mapped_column("oin_certificate", String)
    deleted_at: Mapped[Optional[str]] = mapped_column("deleted_at", String)  # this should be datetime
    status: Mapped[str] = mapped_column("status", String)
