import datetime

from app.db.models.organization import OrganizationEntity
from app.db.models.source import SourceEntity
from app.models.source import SourceUpdate


class SourceService:
    @staticmethod
    def compute_org_sources_for_update(
        org: OrganizationEntity, incoming_sources: list[SourceUpdate]
    ) -> list[SourceEntity]:
        org_source_map = {c.source_id: c for c in org.sources} if org.sources else {}
        if not org_source_map:
            return [s.into_entity(org.id) for s in incoming_sources]

        result: list[SourceEntity] = []
        updated_source_ids: list[str] = []
        for new_source in incoming_sources:
            existing_source = org_source_map.get(new_source.source_id)
            if not existing_source:
                updated_source_ids.append(new_source.source_id)
                result.append(new_source.into_entity(org.id))
                continue

            # TODO: do the same on other updates as well
            # handle pre-existing deleted at
            if existing_source.deleted_at:
                existing_source.deleted_at = None

            if existing_source.name != new_source.name:
                existing_source.name = new_source.name

            updated_source_ids.append(existing_source.source_id)
            result.append(existing_source)

        # mark the rest for delete
        for key, value in org_source_map.items():
            if key not in updated_source_ids:
                value.deleted_at = datetime.datetime.now()
                result.append(value)

        return result
