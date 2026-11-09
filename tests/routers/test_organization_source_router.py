from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.db.repository.source import SourceRepository
from app.models.organization import OrganizationCreate
from app.models.source import Source
from app.services.organization import OrganizationService
from tests.conftest import SECOND_SOURCE_ID, SECOND_SOURCE_NAME, TEST_SOURCE_ID, TEST_SOURCE_NAME


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


def sources_url(org_id: UUID) -> str:
    return f"/organizations/{org_id}/source"


def ids(response_json: list[dict[str, Any]]) -> list[str]:
    return [s["id"] for s in response_json]


@pytest.mark.parametrize(
    "method, path, body",
    [
        ("post", "", {"source_id": "new-source", "name": "New source"}),
        ("get", "", None),
        ("get", f"/{uuid4()}", None),
        ("delete", f"/{uuid4()}", None),
    ],
)
def test_returns_404_when_organization_missing(
    api: TestClient, method: str, path: str, body: dict[str, object] | None
) -> None:
    response = api.request(method, f"{sources_url(uuid4())}{path}", json=body)

    assert response.status_code == 404


def test_register_returns_200(api: TestClient, sources: list[Source]) -> None:
    org_id = sources[0].organization_id

    response = api.post(sources_url(org_id), json={"source_id": "new-source", "name": "New source"})

    assert response.status_code == 200
    body = response.json()
    assert body["source_id"] == "new-source"
    assert body["name"] == "New source"
    assert body["organization_id"] == str(org_id)
    assert api.get(f"{sources_url(org_id)}/{body['id']}").status_code == 200


def test_register_duplicate_source_id_returns_409(api: TestClient, sources: list[Source]) -> None:
    response = api.post(
        sources_url(sources[0].organization_id), json={"source_id": TEST_SOURCE_ID, "name": "Other name"}
    )

    assert response.status_code == 409


@pytest.mark.parametrize("body", [{}, {"source_id": "new-source"}, {"name": "New source"}])
def test_register_invalid_body_returns_422(api: TestClient, sources: list[Source], body: dict[str, object]) -> None:
    response = api.post(sources_url(sources[0].organization_id), json=body)

    assert response.status_code == 422


def test_get_many_returns_list(api: TestClient, sources: list[Source]) -> None:
    response = api.get(sources_url(sources[0].organization_id))

    assert response.status_code == 200
    assert sorted(ids(response.json())) == sorted(str(s.id) for s in sources)


@pytest.mark.parametrize(
    "query, expected_source_ids",
    [
        (f"source_id={TEST_SOURCE_ID}", [TEST_SOURCE_ID]),
        (f"source_id={SECOND_SOURCE_ID}", [SECOND_SOURCE_ID]),
        (f"name={SECOND_SOURCE_NAME}", [SECOND_SOURCE_ID]),
        (f"source_id={TEST_SOURCE_ID}&name={TEST_SOURCE_NAME}", [TEST_SOURCE_ID]),
        (f"source_id={TEST_SOURCE_ID}&name={SECOND_SOURCE_NAME}", []),
        ("source_id=unknown", []),
    ],
)
def test_get_many_applies_query_params(
    api: TestClient, sources: list[Source], query: str, expected_source_ids: list[str]
) -> None:
    response = api.get(f"{sources_url(sources[0].organization_id)}?{query}")

    assert response.status_code == 200
    assert sorted(s["source_id"] for s in response.json()) == expected_source_ids


def test_get_one_returns_200(api: TestClient, sources: list[Source]) -> None:
    target = sources[0]

    response = api.get(f"{sources_url(target.organization_id)}/{target.id}")

    assert response.status_code == 200
    assert response.json()["source_id"] == target.source_id
    assert response.json()["name"] == target.name


def test_get_one_not_found_returns_404(api: TestClient, sources: list[Source]) -> None:
    response = api.get(f"{sources_url(sources[0].organization_id)}/{uuid4()}")

    assert response.status_code == 404


@pytest.mark.parametrize("method", ["get", "delete"])
def test_invalid_uuid_returns_422(api: TestClient, sources: list[Source], method: str) -> None:
    response = api.request(method, f"{sources_url(sources[0].organization_id)}/not-a-uuid")

    assert response.status_code == 422


def test_delete_returns_200_and_soft_deletes(api: TestClient, sources: list[Source]) -> None:
    target, remaining = sources
    url = sources_url(target.organization_id)

    response = api.delete(f"{url}/{target.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(target.id)
    assert api.get(f"{url}/{target.id}").status_code == 404
    assert ids(api.get(url).json()) == [str(remaining.id)]
    assert api.get(f"{url}?source_id={target.source_id}").json() == []


def test_delete_twice_returns_404(api: TestClient, sources: list[Source]) -> None:
    target = sources[0]
    url = f"{sources_url(target.organization_id)}/{target.id}"
    assert api.delete(url).status_code == 200

    response = api.delete(url)

    assert response.status_code == 404


def test_delete_not_found_returns_404(api: TestClient, sources: list[Source]) -> None:
    response = api.delete(f"{sources_url(sources[0].organization_id)}/{uuid4()}")

    assert response.status_code == 404


def test_delete_source_assigned_to_client_returns_409(
    api: TestClient, organization_service: OrganizationService, org_create_dto_1: OrganizationCreate
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    assert org.clients is not None
    client_sources = org.clients[0].sources
    assert client_sources is not None
    url = f"{sources_url(org.id)}/{client_sources[0].id}"

    response = api.delete(url)

    assert response.status_code == 409
    assert api.get(url).status_code == 200
