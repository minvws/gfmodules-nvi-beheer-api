from dataclasses import dataclass
from typing import Any, Self
from uuid import UUID

from app.db.models.client import ClientEntity
from app.db.models.organization import OrganizationEntity
from app.db.models.source import SourceEntity
from app.db.repository.contexts.data import (
    ClientQueryContextBase,
    OrganizationQueryContextBase,
    SourceQueryContextBase,
)


@dataclass()
class SourceOrganizationQueryContext(OrganizationQueryContextBase):
    id: UUID | None = None

    def get_conditions(self) -> list[Any]:
        org_filters = []
        if self.id:
            org_filters.append(OrganizationEntity.id == self.id)

        if self.external_id:
            org_filters.append(OrganizationEntity.external_id == self.external_id)

        if self.name:
            org_filters.append(OrganizationEntity.name == self.name)

        return org_filters

    @classmethod
    def default(cls) -> Self:
        return cls()


@dataclass()
class SourceClientQueryContext(ClientQueryContextBase):
    def get_conditions(self) -> list[Any]:
        client_filters = []
        if self.id:
            client_filters.append(ClientEntity.id == self.id)

        if self.organization_id:
            client_filters.append(ClientEntity.organization_id == self.organization_id)

        if self.name:
            client_filters.append(ClientEntity.name == self.name)

        if self.description:
            client_filters.append(ClientEntity.description == self.description)

        return client_filters

    @classmethod
    def default(cls) -> Self:
        return cls()


@dataclass()
class SourceQueryContext(SourceQueryContextBase):
    organization_id: UUID | None = None
    organization_ctx: SourceOrganizationQueryContext | None = None
    client_ctx: SourceClientQueryContext | None = None

    def get_conditions(self) -> list[Any]:
        conditions = []
        if self.id:
            conditions.append(SourceEntity.id == self.id)

        if self.organization_id:
            conditions.append(SourceEntity.organization_id == self.organization_id)

        if self.name:
            conditions.append(SourceEntity.name == self.name)

        if self.source_id:
            conditions.append(SourceEntity.source_id == self.source_id)

        return conditions
