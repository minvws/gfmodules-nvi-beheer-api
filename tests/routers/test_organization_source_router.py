import pytest
from fastapi.testclient import TestClient

from app.db.repository.source import SourceRepository
from app.models.organization import OrganizationCreate
from app.models.source import Source
from app.services.organization import OrganizationService


@pytest.fixture
def sources(organization_service: OrganizationService, org_create_dto_1: OrganizationCreate) -> list[Source]:
    org_create_dto_1.clients = None
    org = organization_service.create_one(org_create_dto_1)
    assert org.sources is not None
    return org.sources


def assert_update_conflicts(api: TestClient, target: Source, source_id: str) -> None:
    response = api.put(
        f"/organizations/{target.organization_id}/source/{target.id}",
        json={"id": str(target.id), "source_id": source_id, "name": target.name},
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": f"Organization {target.organization_id} already has a source {source_id} assigned"
    }


def test_update_to_existing_source_id_returns_409(api: TestClient, sources: list[Source]) -> None:
    existing, target = sources

    assert_update_conflicts(api, target, existing.source_id)


def test_update_to_existing_source_id_caught_by_database_returns_409(
    api: TestClient, sources: list[Source], monkeypatch: pytest.MonkeyPatch
) -> None:
    existing, target = sources
    monkeypatch.setattr(SourceRepository, "find_many", lambda *_args, **_kwargs: [])

    assert_update_conflicts(api, target, existing.source_id)
