from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.models.organization import OrganizationCreate
from tests.conftest import SECOND_EXTERNAL_ID, TEST_DOMAIN, TEST_EXTERNAL_ID, TEST_OIN, TEST_ORG_NAME

RESOLVE = "/clients/resolve"


def _body(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "client_id": str(uuid4()),
        "organization_external_id": TEST_EXTERNAL_ID.value,
        "certificate_organization_identifier": str(TEST_OIN),
        "certificate_domains": [TEST_DOMAIN],
    }
    body.update(overrides)
    return body


def test_resolve_returns_200(
    api: TestClient,
    organization_service: object,
    org_create_dto_1: OrganizationCreate,
) -> None:
    org = organization_service.create_one(org_create_dto_1)  # type: ignore[attr-defined]
    assert org.clients is not None
    client = org.clients[0]

    response = api.post(RESOLVE, json=_body(client_id=str(client.id)))

    assert response.status_code == 200
    body = response.json()
    assert body["organization_name"] == TEST_ORG_NAME
    assert body["matched_domain"] == TEST_DOMAIN


def test_resolve_not_found_returns_404(api: TestClient) -> None:
    response = api.post(RESOLVE, json=_body())
    assert response.status_code == 404


def test_resolve_organization_mismatch_returns_404(
    api: TestClient,
    organization_service: object,
    org_create_dto_1: OrganizationCreate,
) -> None:
    org = organization_service.create_one(org_create_dto_1)  # type: ignore[attr-defined]
    assert org.clients is not None
    client = org.clients[0]

    response = api.post(
        RESOLVE, json=_body(client_id=str(client.id), organization_external_id=SECOND_EXTERNAL_ID.value)
    )

    assert response.status_code == 404


@pytest.mark.parametrize(
    "body",
    [
        {  # missing client_id
            "organization_external_id": TEST_EXTERNAL_ID.value,
            "certificate_organization_identifier": str(TEST_OIN),
            "certificate_domains": [TEST_DOMAIN],
        },
        {  # missing organization_external_id
            "client_id": str(uuid4()),
            "certificate_organization_identifier": str(TEST_OIN),
            "certificate_domains": [TEST_DOMAIN],
        },
        {  # missing certificate_organization_identifier
            "client_id": str(uuid4()),
            "organization_external_id": TEST_EXTERNAL_ID.value,
            "certificate_domains": [TEST_DOMAIN],
        },
        {  # missing certificate_domains
            "client_id": str(uuid4()),
            "organization_external_id": TEST_EXTERNAL_ID.value,
            "certificate_organization_identifier": str(TEST_OIN),
        },
        {  # certificate_domains not a list
            "client_id": str(uuid4()),
            "organization_external_id": TEST_EXTERNAL_ID.value,
            "certificate_organization_identifier": str(TEST_OIN),
            "certificate_domains": TEST_DOMAIN,
        },
        {  # malformed certificate_organization_identifier
            "client_id": str(uuid4()),
            "organization_external_id": TEST_EXTERNAL_ID.value,
            "certificate_organization_identifier": "invalid-oin",
            "certificate_domains": [TEST_DOMAIN],
        },
        {  # malformed client_id
            "client_id": "not-a-uuid",
            "organization_external_id": TEST_EXTERNAL_ID.value,
            "certificate_organization_identifier": str(TEST_OIN),
            "certificate_domains": [TEST_DOMAIN],
        },
    ],
)
def test_resolve_invalid_body_returns_422(api: TestClient, body: dict[str, object]) -> None:
    response = api.post(RESOLVE, json=body)
    assert response.status_code == 422
