from uuid import UUID

from gfmodules.logging import set_context


def organization_in_context(organization_id: UUID) -> None:
    set_context({"organization_id": str(organization_id)})


def organization_id_in_context(id: UUID) -> None:
    set_context({"organization_id": str(id)})
