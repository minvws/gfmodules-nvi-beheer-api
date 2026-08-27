from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Self
from uuid import UUID

from app.db.repository.query_builder.context.data import (
    ClientQueryContextBase,
    OrganizationQueryContextBase,
    SourceQueryContextBase,
)


class SourceRelations(Enum):
    ORGANIZATION = auto()
    CLIENTS = auto()


@dataclass()
class SourceOrganizationQueryContext(OrganizationQueryContextBase):
    id: UUID | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "external_id": self.external_id}

    @classmethod
    def default(cls) -> Self:
        return cls()


@dataclass()
class SourceClientQueryContext(ClientQueryContextBase):
    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "description": self.description}

    @classmethod
    def default(cls) -> Self:
        return cls()


@dataclass()
class SourceQueryContext(SourceQueryContextBase):
    organization_ctx: SourceOrganizationQueryContext | None = None
    client_ctx: SourceClientQueryContext | None = None

    @property
    def include(self) -> set[SourceRelations]:
        relantions = set()
        if self.organization_ctx:
            relantions.add(SourceRelations.ORGANIZATION)

        if self.client_ctx:
            relantions.add(SourceRelations.ORGANIZATION)

        return relantions
