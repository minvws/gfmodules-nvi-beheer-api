from dataclasses import dataclass
from typing import Self
from uuid import UUID

from app.models.oin import Oin
from app.models.ura import UraNumber


@dataclass()
class SourceQueryContextBase:
    id: UUID | None = None
    source_id: str | None = None
    name: str | None = None

    @classmethod
    def default(cls) -> Self:
        return cls()


@dataclass
class CertificateQueryContextBase:
    id: UUID | None = None
    organization_identifier: Oin | None = None
    domain: str | None = None

    @classmethod
    def default(cls) -> Self:
        return cls()


@dataclass
class ClientQueryContextBase:
    id: UUID | None = None
    organization_id: UUID | None = None
    name: str | None = None
    description: str | None = None


@dataclass
class OrganizationQueryContextBase:
    external_id: UraNumber | None = None
    name: str | None = None
