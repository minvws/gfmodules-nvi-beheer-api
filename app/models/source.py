from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.db.models.source import SourceEntity
from app.models.base import CommonModel


class SourceFields(BaseModel):
    source_id: str
    name: str

    def into_entity(self, organization_id: UUID | None = None) -> SourceEntity:
        source = SourceEntity(source_id=self.source_id, name=self.name)
        if organization_id:
            source.organization_id = organization_id

        return source


class SourceCreate(SourceFields):
    pass


class SourceUpdate(SourceFields):
    @classmethod
    def from_entity(cls, entity: SourceEntity) -> Self:
        return cls(source_id=entity.source_id, name=entity.name)


class Source(SourceFields, CommonModel):
    organization_id: UUID
    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_entity(cls, entity: SourceEntity) -> Self:
        return cls(
            id=entity.id,
            organization_id=entity.organization_id,
            source_id=entity.source_id,
            name=entity.name,
            created_at=entity.created_at,
        )
