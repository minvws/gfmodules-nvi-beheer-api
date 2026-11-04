from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.models.client import ClientCreate
from app.models.organization import OrganizationCreate
from app.models.source import Source, SourceCreate
from app.services.organization import OrganizationService
from tests.conftest import SECOND_SOURCE_ID, TEST_SOURCE_ID, TEST_SOURCE_NAME


@dataclass
class Setup:
    org_id: UUID
    client_id: UUID
    assigned: Source
    unassigned: Source

    @property
    def url(self) -> str:
        return sources_url(self.org_id, self.client_id)


def sources_url(org_id: UUID, client_id: UUID) -> str:
    return f"/organizations/{org_id}/clients/{client_id}/sources"


@pytest.fixture
def setup(
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
    client_create_dto_1: ClientCreate,
    source_create_dto_1: SourceCreate,
) -> Setup:
    """An organization with two sources; its single client is assigned only the first one."""
    client_create_dto_1.sources = [source_create_dto_1]
    org = organization_service.create_one(org_create_dto_1)
    assert org.sources is not None
    assert org.clients is not None
    by_source_id = {s.source_id: s for s in org.sources}
    return Setup(
        org_id=org.id,
        client_id=org.clients[0].id,
        assigned=by_source_id[TEST_SOURCE_ID],
        unassigned=by_source_id[SECOND_SOURCE_ID],
    )


def ids(response_json: list[dict[str, Any]]) -> list[str]:
    return [s["id"] for s in response_json]


def parent_missing_url(setup: Setup, missing: str) -> str:
    if missing == "organization":
        return sources_url(uuid4(), setup.client_id)
    return sources_url(setup.org_id, uuid4())


@pytest.mark.parametrize("method", ["get", "post", "delete"])
@pytest.mark.parametrize("missing", ["organization", "client"])
def test_returns_404_when_parent_missing(api: TestClient, setup: Setup, method: str, missing: str) -> None:
    url = parent_missing_url(setup, missing)

    response = api.request(method, f"{url}/{setup.assigned.id}")

    assert response.status_code == 404


@pytest.mark.parametrize("missing", ["organization", "client"])
def test_get_many_returns_404_when_parent_missing(api: TestClient, setup: Setup, missing: str) -> None:
    response = api.get(parent_missing_url(setup, missing))

    assert response.status_code == 404


def test_get_many_returns_only_assigned_sources(api: TestClient, setup: Setup) -> None:
    response = api.get(setup.url)

    assert response.status_code == 200
    assert ids(response.json()) == [str(setup.assigned.id)]


@pytest.mark.parametrize("query", [f"source_id={TEST_SOURCE_ID}", f"name={TEST_SOURCE_NAME}"])
def test_get_many_filter_matches(api: TestClient, setup: Setup, query: str) -> None:
    response = api.get(f"{setup.url}?{query}")

    assert response.status_code == 200
    assert ids(response.json()) == [str(setup.assigned.id)]


@pytest.mark.parametrize("query", [f"source_id={SECOND_SOURCE_ID}", "name=unknown"])
def test_get_many_filter_excludes(api: TestClient, setup: Setup, query: str) -> None:
    response = api.get(f"{setup.url}?{query}")

    assert response.status_code == 200
    assert response.json() == []


def test_get_one_returns_200(api: TestClient, setup: Setup) -> None:
    response = api.get(f"{setup.url}/{setup.assigned.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(setup.assigned.id)
    assert body["source_id"] == TEST_SOURCE_ID
    assert body["name"] == TEST_SOURCE_NAME
    assert body["organization_id"] == str(setup.org_id)


def test_get_one_unassigned_source_returns_404(api: TestClient, setup: Setup) -> None:
    response = api.get(f"{setup.url}/{setup.unassigned.id}")

    assert response.status_code == 404


@pytest.mark.parametrize("method", ["get", "post", "delete"])
def test_invalid_uuid_returns_422(api: TestClient, setup: Setup, method: str) -> None:
    response = api.request(method, f"{setup.url}/not-a-uuid")

    assert response.status_code == 422


def test_assign_returns_200(api: TestClient, setup: Setup) -> None:
    response = api.post(f"{setup.url}/{setup.unassigned.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(setup.unassigned.id)
    assert sorted(ids(api.get(setup.url).json())) == sorted([str(setup.assigned.id), str(setup.unassigned.id)])


def test_assign_already_assigned_returns_409(api: TestClient, setup: Setup) -> None:
    response = api.post(f"{setup.url}/{setup.assigned.id}")

    assert response.status_code == 409


def test_assign_unknown_source_returns_404(api: TestClient, setup: Setup) -> None:
    response = api.post(f"{setup.url}/{uuid4()}")

    assert response.status_code == 404


def test_assign_soft_deleted_source_returns_404(api: TestClient, setup: Setup) -> None:
    assert api.delete(f"/organizations/{setup.org_id}/source/{setup.unassigned.id}").status_code == 200

    response = api.post(f"{setup.url}/{setup.unassigned.id}")

    assert response.status_code == 404


def test_unassign_returns_200(api: TestClient, setup: Setup) -> None:
    response = api.delete(f"{setup.url}/{setup.assigned.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(setup.assigned.id)
    assert api.get(f"{setup.url}/{setup.assigned.id}").status_code == 404
    assert api.get(setup.url).json() == []


def test_unassign_not_assigned_source_returns_404(api: TestClient, setup: Setup) -> None:
    response = api.delete(f"{setup.url}/{setup.unassigned.id}")

    assert response.status_code == 404


def test_unassign_unknown_source_returns_404(api: TestClient, setup: Setup) -> None:
    response = api.delete(f"{setup.url}/{uuid4()}")

    assert response.status_code == 404
