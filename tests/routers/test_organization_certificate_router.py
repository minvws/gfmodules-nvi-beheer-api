from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.db.repository.certificate import CertificateRepository
from app.models.certificates import Certificate, CertificateCreate
from app.models.organization import Organization, OrganizationCreate
from app.services.organization import OrganizationService
from tests.conftest import SECOND_DOMAIN, SECOND_OIN, TEST_DOMAIN, TEST_OIN


@pytest.fixture
def org(
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
    cert_create_dto_1: CertificateCreate,
) -> Organization:
    org_create_dto_1.clients = None
    org_create_dto_1.certificates = [
        cert_create_dto_1,
        CertificateCreate(organization_identifier=SECOND_OIN, domain=TEST_DOMAIN),
    ]
    return organization_service.create_one(org_create_dto_1)


def assert_update_conflicts(api: TestClient, org: Organization, target: Certificate, existing: Certificate) -> None:
    response = api.put(
        f"/organizations/{org.id}/certificate/{target.id}",
        json={
            "id": str(target.id),
            "organization_identifier": str(existing.organization_identifier),
            "domain": existing.domain,
        },
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": f"Certificate with organization_identifier: {existing.organization_identifier}, "
        f"domain: {existing.domain} already exists"
    }


def test_update_to_existing_identifier_and_domain_returns_409(api: TestClient, org: Organization) -> None:
    assert org.certificates is not None
    existing, target = org.certificates

    assert_update_conflicts(api, org, target, existing)


def test_update_to_existing_identifier_and_domain_caught_by_database_returns_409(
    api: TestClient, org: Organization, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert org.certificates is not None
    existing, target = org.certificates
    monkeypatch.setattr(CertificateRepository, "find_many", lambda *_args, **_kwargs: [])

    assert_update_conflicts(api, org, target, existing)


def test_update_domain_returns_200(api: TestClient, org: Organization) -> None:
    assert org.certificates is not None
    target = org.certificates[0]
    url = f"/organizations/{org.id}/certificate/{target.id}"

    response = api.put(
        url,
        json={
            "id": str(target.id),
            "organization_identifier": str(target.organization_identifier),
            "domain": "new.example",
        },
    )

    assert response.status_code == 200
    assert response.json()["domain"] == "new.example"
    assert api.get(url).json()["domain"] == "new.example"


def certs_url(org: Organization) -> str:
    return f"/organizations/{org.id}/certificate"


def ids(response_json: list[dict[str, Any]]) -> list[str]:
    return [c["id"] for c in response_json]


@pytest.mark.parametrize(
    "method, path, body",
    [
        ("post", "", {"organization_identifier": str(TEST_OIN), "domain": "new.example"}),
        ("get", "", None),
        ("get", f"/{uuid4()}", None),
        ("delete", f"/{uuid4()}", None),
    ],
)
def test_returns_404_when_organization_missing(
    api: TestClient, method: str, path: str, body: dict[str, object] | None
) -> None:
    response = api.request(method, f"/organizations/{uuid4()}/certificate{path}", json=body)

    assert response.status_code == 404


def test_register_returns_200(api: TestClient, org: Organization) -> None:
    response = api.post(certs_url(org), json={"organization_identifier": str(TEST_OIN), "domain": "new.example"})

    assert response.status_code == 200
    body = response.json()
    assert body["organization_identifier"] == str(TEST_OIN)
    assert body["domain"] == "new.example"
    assert api.get(f"{certs_url(org)}/{body['id']}").status_code == 200


def test_register_duplicate_returns_409(api: TestClient, org: Organization) -> None:
    response = api.post(certs_url(org), json={"organization_identifier": str(TEST_OIN), "domain": TEST_DOMAIN})

    assert response.status_code == 409


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"domain": TEST_DOMAIN},
        {"organization_identifier": str(TEST_OIN)},
        {"organization_identifier": "invalid-oin", "domain": TEST_DOMAIN},
    ],
)
def test_register_invalid_body_returns_422(api: TestClient, org: Organization, body: dict[str, object]) -> None:
    response = api.post(certs_url(org), json=body)

    assert response.status_code == 422


def test_get_many_returns_list(api: TestClient, org: Organization) -> None:
    assert org.certificates is not None

    response = api.get(certs_url(org))

    assert response.status_code == 200
    assert sorted(ids(response.json())) == sorted(str(c.id) for c in org.certificates)


@pytest.mark.parametrize(
    "query, expected_identifiers",
    [
        (f"organization_identifier={TEST_OIN!s}", [str(TEST_OIN)]),
        (f"organization_identifier={SECOND_OIN!s}", [str(SECOND_OIN)]),
        (f"domain={TEST_DOMAIN}", sorted([str(TEST_OIN), str(SECOND_OIN)])),
        (f"domain={SECOND_DOMAIN}", []),
        (f"organization_identifier={SECOND_OIN!s}&domain={TEST_DOMAIN}", [str(SECOND_OIN)]),
    ],
)
def test_get_many_applies_query_params(
    api: TestClient, org: Organization, query: str, expected_identifiers: list[str]
) -> None:
    response = api.get(f"{certs_url(org)}?{query}")

    assert response.status_code == 200
    assert sorted(c["organization_identifier"] for c in response.json()) == expected_identifiers


@pytest.mark.parametrize("query", ["include_deleted=maybe", "organization_identifier=invalid-oin", "unknown=value"])
def test_get_many_invalid_query_returns_422(api: TestClient, org: Organization, query: str) -> None:
    response = api.get(f"{certs_url(org)}?{query}")

    assert response.status_code == 422


def test_get_by_id_not_found_returns_404(api: TestClient, org: Organization) -> None:
    response = api.get(f"{certs_url(org)}/{uuid4()}")

    assert response.status_code == 404


@pytest.mark.parametrize("method", ["get", "delete"])
def test_invalid_uuid_returns_422(api: TestClient, org: Organization, method: str) -> None:
    response = api.request(method, f"{certs_url(org)}/not-a-uuid")

    assert response.status_code == 422


def test_delete_returns_200_and_soft_deletes(api: TestClient, org: Organization) -> None:
    assert org.certificates is not None
    target, remaining = org.certificates

    response = api.delete(f"{certs_url(org)}/{target.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(target.id)
    assert api.get(f"{certs_url(org)}/{target.id}").status_code == 404
    assert ids(api.get(certs_url(org)).json()) == [str(remaining.id)]
    assert ids(api.get(f"{certs_url(org)}?include_deleted=false").json()) == [str(remaining.id)]
    including_deleted = api.get(f"{certs_url(org)}?include_deleted=true").json()
    assert sorted(ids(including_deleted)) == sorted([str(target.id), str(remaining.id)])


def test_delete_twice_returns_404(api: TestClient, org: Organization) -> None:
    assert org.certificates is not None
    url = f"{certs_url(org)}/{org.certificates[0].id}"
    assert api.delete(url).status_code == 200

    response = api.delete(url)

    assert response.status_code == 404


def test_delete_not_found_returns_404(api: TestClient, org: Organization) -> None:
    response = api.delete(f"{certs_url(org)}/{uuid4()}")

    assert response.status_code == 404


def test_delete_certificate_assigned_to_client_returns_409(
    api: TestClient, organization_service: OrganizationService, org_create_dto_1: OrganizationCreate
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    assert org.clients is not None
    client_certs = org.clients[0].certificates
    assert client_certs is not None

    response = api.delete(f"{certs_url(org)}/{client_certs[0].id}")

    assert response.status_code == 409
    assert api.get(f"{certs_url(org)}/{client_certs[0].id}").status_code == 200
