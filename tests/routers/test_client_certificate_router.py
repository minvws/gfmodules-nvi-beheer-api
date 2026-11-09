from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.models.certificates import Certificate
from app.models.organization import OrganizationCreate
from app.services.organization import OrganizationService
from tests.conftest import SECOND_DOMAIN, SECOND_OIN, TEST_DOMAIN, TEST_OIN


@dataclass
class Setup:
    org_id: UUID
    client_id: UUID
    assigned: Certificate
    unassigned: Certificate

    @property
    def url(self) -> str:
        return certificates_url(self.org_id, self.client_id)


def certificates_url(org_id: UUID, client_id: UUID) -> str:
    return f"/organizations/{org_id}/clients/{client_id}/certificate"


@pytest.fixture
def setup(organization_service: OrganizationService, org_create_dto_1: OrganizationCreate) -> Setup:
    """An organization with two certificates; its single client is assigned only the first one."""
    org = organization_service.create_one(org_create_dto_1)
    assert org.certificates is not None
    assert org.clients is not None
    by_domain = {c.domain: c for c in org.certificates}
    return Setup(
        org_id=org.id,
        client_id=org.clients[0].id,
        assigned=by_domain[TEST_DOMAIN],
        unassigned=by_domain[SECOND_DOMAIN],
    )


def ids(response_json: list[dict[str, Any]]) -> list[str]:
    return [c["id"] for c in response_json]


def parent_missing_url(setup: Setup, missing: str) -> str:
    if missing == "organization":
        return certificates_url(uuid4(), setup.client_id)
    return certificates_url(setup.org_id, uuid4())


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


def test_get_many_returns_only_assigned_certificates(api: TestClient, setup: Setup) -> None:
    response = api.get(setup.url)

    assert response.status_code == 200
    assert ids(response.json()) == [str(setup.assigned.id)]


@pytest.mark.parametrize(
    "query",
    [f"domain={TEST_DOMAIN}", f"organization_identifier={TEST_OIN!s}"],
)
def test_get_many_filter_matches(api: TestClient, setup: Setup, query: str) -> None:
    response = api.get(f"{setup.url}?{query}")

    assert response.status_code == 200
    assert ids(response.json()) == [str(setup.assigned.id)]


@pytest.mark.parametrize(
    "query",
    ["domain=unknown.example", f"organization_identifier={SECOND_OIN!s}"],
)
def test_get_many_filter_excludes(api: TestClient, setup: Setup, query: str) -> None:
    response = api.get(f"{setup.url}?{query}")

    assert response.status_code == 200
    assert response.json() == []


def test_get_many_invalid_organization_identifier_returns_422(api: TestClient, setup: Setup) -> None:
    response = api.get(f"{setup.url}?organization_identifier=invalid-oin")

    assert response.status_code == 422


def test_get_one_returns_200(api: TestClient, setup: Setup) -> None:
    response = api.get(f"{setup.url}/{setup.assigned.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(setup.assigned.id)
    assert body["domain"] == TEST_DOMAIN
    assert body["organization_identifier"] == str(TEST_OIN)


def test_get_one_unassigned_certificate_returns_404(api: TestClient, setup: Setup) -> None:
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


def test_assign_unknown_certificate_returns_404(api: TestClient, setup: Setup) -> None:
    response = api.post(f"{setup.url}/{uuid4()}")

    assert response.status_code == 404


def test_assign_soft_deleted_certificate_returns_404(api: TestClient, setup: Setup) -> None:
    assert api.delete(f"/organizations/{setup.org_id}/certificate/{setup.unassigned.id}").status_code == 200

    response = api.post(f"{setup.url}/{setup.unassigned.id}")

    assert response.status_code == 404


def test_unassign_returns_200(api: TestClient, setup: Setup) -> None:
    response = api.delete(f"{setup.url}/{setup.assigned.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(setup.assigned.id)
    assert api.get(f"{setup.url}/{setup.assigned.id}").status_code == 404
    assert api.get(setup.url).json() == []


def test_unassign_not_assigned_certificate_returns_404(api: TestClient, setup: Setup) -> None:
    response = api.delete(f"{setup.url}/{setup.unassigned.id}")

    assert response.status_code == 404


def test_unassign_unknown_certificate_returns_404(api: TestClient, setup: Setup) -> None:
    response = api.delete(f"{setup.url}/{uuid4()}")

    assert response.status_code == 404
