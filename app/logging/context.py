from uuid import UUID

from gfmodules.logging import set_context

from app.logging.events import ORGANIZATION


def organization_in_context(organization_id: UUID) -> None:
    set_context({ORGANIZATION.name: str(organization_id)})
