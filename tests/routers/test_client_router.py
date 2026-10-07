from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.models.certificates import CertificateCreate
from app.models.client import ClientCreate
from app.models.organization import OrganizationCreate
from app.models.scopes import AuthorizationScope
from app.models.source import SourceCreate
from app.services.organization import OrganizationService
from tests.conftest import (
    SECOND_DOMAIN,
    SECOND_OIN,
    SECOND_SOURCE_ID,
    SECOND_SOURCE_NAME,
    TEST_CLIENT_NAME,
    TEST_DOMAIN,
    TEST_EXTERNAL_ID,
    TEST_OIN,
    TEST_ORG_NAME,
    TEST_SOURCE_ID,
    TEST_SOURCE_NAME,
    VALID_OIN,
)

ORG_ID = "11111111-1111-1111-1111-111111111111"
CLIENT_ID = "22222222-2222-2222-2222-222222222222"
BASE = f"/organizations/{ORG_ID}/clients"


@pytest.mark.parametrize(
    "method, path, body",
    [
        ("post", BASE, {"name": "C"}),
        ("get", f"{BASE}/{CLIENT_ID}", None),
        ("get", BASE, None),
        ("put", f"{BASE}/{CLIENT_ID}", {"id": str(CLIENT_ID), "name": "C"}),
        ("delete", f"{BASE}/{CLIENT_ID}", None),
    ],
)
def test_returns_404_when_organization_missing(
    api: TestClient,
    method: str,
    path: str,
    body: dict[str, object] | None,
) -> None:
    response = api.request(method, path, json=body)
    assert response.status_code == 404


def test_register_returns_201(
    api: TestClient,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
    client_create_dto_1: ClientCreate,
) -> None:
    org_create_dto_1.clients = None
    org = organization_service.create_one(org_create_dto_1)

    response = api.post(f"/organizations/{org.id!s}/clients", json=client_create_dto_1.model_dump())

    assert response.status_code == 201


def test_register_duplicate_certificates_returns_422(
    api: TestClient, organization_service: OrganizationService, org_create_dto_1: OrganizationCreate
) -> None:
    org_create_dto_1.clients = None
    org = organization_service.create_one(org_create_dto_1)
    body = {
        "name": TEST_CLIENT_NAME,
        "certificates": [
            {"organization_identifier": str(TEST_OIN), "domain": TEST_DOMAIN},
            {"organization_identifier": str(TEST_OIN), "domain": TEST_DOMAIN},
        ],
    }

    response = api.post(f"/organizations/{org.id}/clients", json=body)

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert len(errors) == 1
    assert errors[0]["loc"] == ["body", "certificates"]
    assert errors[0]["type"] == "value_error"
    assert errors[0]["msg"] == f"Value error, Duplicate certificate values: {TEST_OIN}/{TEST_DOMAIN}"
    assert api.get(f"/organizations/{org.id}/clients").json() == []


def test_register_allows_an_organization_certificate_subset(
    api: TestClient, organization_service: OrganizationService, org_create_dto_1: OrganizationCreate
) -> None:
    org_create_dto_1.clients = None
    org = organization_service.create_one(org_create_dto_1)
    assert org.certificates is not None
    assert len(org.certificates) == 2

    response = api.post(
        f"/organizations/{org.id}/clients",
        json={
            "name": TEST_CLIENT_NAME,
            "certificates": [{"organization_identifier": str(TEST_OIN), "domain": TEST_DOMAIN}],
        },
    )

    assert response.status_code == 201
    certificates = response.json()["certificates"]
    assert len(certificates) == 1
    assert certificates[0]["id"] == str(org.certificates[0].id)


def test_register_duplicate_source_ids_returns_422(
    api: TestClient, organization_service: OrganizationService, org_create_dto_1: OrganizationCreate
) -> None:
    org_create_dto_1.clients = None
    org = organization_service.create_one(org_create_dto_1)
    body = {
        "name": TEST_CLIENT_NAME,
        "sources": [
            {"source_id": TEST_SOURCE_ID, "name": TEST_SOURCE_NAME},
            {"source_id": TEST_SOURCE_ID, "name": SECOND_SOURCE_NAME},
        ],
    }

    response = api.post(f"/organizations/{org.id}/clients", json=body)

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert len(errors) == 1
    assert errors[0]["loc"] == ["body", "sources"]
    assert errors[0]["type"] == "value_error"
    assert errors[0]["msg"] == f"Value error, Duplicate source_id values: {TEST_SOURCE_ID}"
    assert api.get(f"/organizations/{org.id}/clients").json() == []


def test_register_allows_an_organization_source_subset(
    api: TestClient, organization_service: OrganizationService, org_create_dto_1: OrganizationCreate
) -> None:
    org_create_dto_1.clients = None
    org = organization_service.create_one(org_create_dto_1)
    assert org.sources is not None
    assert len(org.sources) == 2

    response = api.post(
        f"/organizations/{org.id}/clients",
        json={"name": TEST_CLIENT_NAME, "sources": [{"source_id": TEST_SOURCE_ID, "name": "Reference"}]},
    )

    assert response.status_code == 201
    sources = response.json()["sources"]
    assert len(sources) == 1
    assert sources[0]["id"] == str(org.sources[0].id)
    assert sources[0]["organization_id"] == str(org.id)


def test_register_ungranted_scope_returns_403(
    api: TestClient,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
    client_create_dto_1: ClientCreate,
) -> None:
    org_create_dto_1.clients = None
    org_create_dto_1.scopes = [AuthorizationScope("nvi:create"), AuthorizationScope("nvi:read")]
    client_create_dto_1.scopes = [AuthorizationScope("nvi:localize")]
    org = organization_service.create_one(org_create_dto_1)

    response = api.post(f"/organizations/{org.id!s}/clients", json=client_create_dto_1.model_dump())

    assert response.status_code == 403


@pytest.mark.parametrize(
    "org_dto, client_dto",
    [
        (
            OrganizationCreate(
                external_id=TEST_EXTERNAL_ID,
                name=TEST_ORG_NAME,
                certificates=[CertificateCreate(organization_identifier=TEST_OIN, domain=TEST_DOMAIN)],
            ),
            ClientCreate(
                name=TEST_CLIENT_NAME,
                certificates=[CertificateCreate(organization_identifier=SECOND_OIN, domain=SECOND_DOMAIN)],
            ),
        ),
        (
            OrganizationCreate(
                external_id=TEST_EXTERNAL_ID,
                name=TEST_ORG_NAME,
                sources=[SourceCreate(source_id=TEST_SOURCE_ID, name=TEST_SOURCE_NAME)],
            ),
            ClientCreate(
                name=TEST_CLIENT_NAME,
                sources=[SourceCreate(source_id=SECOND_SOURCE_ID, name=SECOND_SOURCE_NAME)],
            ),
        ),
        (
            OrganizationCreate(
                external_id=TEST_EXTERNAL_ID,
                name=TEST_ORG_NAME,
                sources=[SourceCreate(source_id=TEST_SOURCE_ID, name=TEST_SOURCE_NAME)],
            ),
            ClientCreate(
                name=TEST_CLIENT_NAME,
                certificates=[CertificateCreate(organization_identifier=SECOND_OIN, domain=SECOND_DOMAIN)],
            ),
        ),
        (
            OrganizationCreate(
                external_id=TEST_EXTERNAL_ID,
                name=TEST_ORG_NAME,
                certificates=[CertificateCreate(organization_identifier=SECOND_OIN, domain=SECOND_DOMAIN)],
            ),
            ClientCreate(
                name=TEST_CLIENT_NAME,
                sources=[SourceCreate(source_id=TEST_SOURCE_ID, name=TEST_SOURCE_NAME)],
            ),
        ),
    ],
)
def test_register_conflict_returns_403(
    api: TestClient,
    organization_service: OrganizationService,
    org_dto: OrganizationCreate,
    client_dto: ClientCreate,
) -> None:
    org = organization_service.create_one(org_dto)
    response = api.post(f"/organizations/{org.id!s}/clients", json=client_dto.model_dump())
    assert response.status_code == 403


@pytest.mark.parametrize(
    "body",
    [
        {"common_name": "C"},  # missing oin
        {"oin": str(VALID_OIN)},  # missing common_name
        {"oin": "invalid-oin", "common_name": "C"},  # malformed oin
    ],
)
def test_register_invalid_body_returns_422(
    api: TestClient, mock_client_service: MagicMock, body: dict[str, object]
) -> None:
    response = api.post(BASE, json=body)
    assert response.status_code == 422
    mock_client_service.create_one.assert_not_called()


def test_get_by_id_returns_200(
    api: TestClient, organization_service: OrganizationService, org_create_dto_1: OrganizationCreate
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    assert org.clients is not None
    target = org.clients[0]

    response = api.get(f"/organizations/{org.id!s}/clients/{target.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(target.id)


def test_get_by_id_not_found_returns_404(api: TestClient) -> None:
    response = api.get(f"/organizations/{uuid4()}/clients/{uuid4()}")
    assert response.status_code == 404


@pytest.mark.parametrize(
    "path",
    [
        # bad organization_id
        f"/organizations/not-a-uuid/clients/{CLIENT_ID}",
        f"{BASE}/not-a-uuid",  # bad client id
    ],
)
def test_get_by_id_invalid_uuid_returns_422(api: TestClient, path: str) -> None:
    response = api.get(path)
    assert response.status_code == 422


def test_get_many_returns_list(
    api: TestClient, organization_service: OrganizationService, org_create_dto_1: OrganizationCreate
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    response = api.get(f"/organizations/{org.id}/clients")
    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.parametrize("query", ["oin=invalid-oin", "include_deleted=maybe"])
def test_get_many_invalid_query_returns_422(api: TestClient, query: str) -> None:
    response = api.get(f"/organizations/{uuid4()}/clients?{query}")
    assert response.status_code == 422


def test_update_returns_200(
    api: TestClient, organization_service: OrganizationService, org_create_dto_1: OrganizationCreate
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    assert org.clients is not None
    target = org.clients[0]
    response = api.put(
        f"/organizations/{org.id!s}/clients/{target.id!s}", json={"id": str(target.id), "name": "Updated"}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated"


def test_update_not_found_returns_404(api: TestClient) -> None:
    response = api.put(f"/organizations/{uuid4()!s}/clients/{uuid4()!s}", json={"id": str(uuid4()), "name": "X"})
    assert response.status_code == 404


def test_update_ungranted_scope_returns_403(
    api: TestClient, organization_service: OrganizationService, org_create_dto_1: OrganizationCreate
) -> None:
    org_create_dto_1.scopes = [AuthorizationScope("nvi:create"), AuthorizationScope("nvi:read")]
    org = organization_service.create_one(org_create_dto_1)
    assert org.clients is not None
    target = org.clients[0]

    response = api.put(
        f"/organizations/{org.id!s}/clients/{target.id!s}",
        json={"id": str(target.id), "name": "some name", "scopes": ["nvi:delete"]},
    )

    assert response.status_code == 403


def test_delete_returns_204(
    api: TestClient, organization_service: OrganizationService, org_create_dto_1: OrganizationCreate
) -> None:
    assert org_create_dto_1.clients is not None
    org_create_dto_1.clients[0].sources = None
    org_create_dto_1.clients[0].certificates = None

    org = organization_service.create_one(org_create_dto_1)
    assert org.clients is not None
    client = org.clients[0]

    response = api.delete(f"/organizations/{org.id!s}/clients/{client.id!s}")
    assert response.status_code == 204


def test_delete_not_found_returns_404(api: TestClient) -> None:
    response = api.delete(f"/organizations/{uuid4()!s}/clients/{uuid4()!s}")
    assert response.status_code == 404


def test_delete_return_409(
    api: TestClient, organization_service: OrganizationService, org_create_dto_1: OrganizationCreate
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    assert org.clients is not None
    client = org.clients[0]

    response = api.delete(f"/organizations/{org.id!s}/clients/{client.id!s}")
    assert response.status_code == 409
    assert client.sources is not None
    assert client.certificates is not None
