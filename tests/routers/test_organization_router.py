from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.models.certificates import CertificateCreate
from app.models.client import ClientCreate
from app.models.organization import OrganizationCreate
from app.models.source import SourceCreate
from app.services.organization import OrganizationService
from tests.conftest import (
    SECOND_DOMAIN,
    SECOND_EXTERNAL_ID,
    SECOND_OIN,
    SECOND_ORG_NAME,
    SECOND_SOURCE_ID,
    SECOND_SOURCE_NAME,
    TEST_CLIENT_NAME,
    TEST_DOMAIN,
    TEST_EXTERNAL_ID,
    TEST_OIN,
    TEST_ORG_NAME,
    TEST_SOURCE_ID,
    TEST_SOURCE_NAME,
)

ORG_ID = "11111111-1111-1111-1111-111111111111"


def test_register_should_succeed(api: TestClient, org_create_dto_1: OrganizationCreate) -> None:
    response = api.post("/organizations", json=org_create_dto_1.model_dump())
    assert response.status_code == 201


@pytest.mark.parametrize(
    "body",
    [
        # unknown scopes
        OrganizationCreate(external_id=TEST_EXTERNAL_ID, name=TEST_ORG_NAME, scopes="some:scopes"),
        # mismatch in org client scope
        OrganizationCreate(
            external_id=TEST_EXTERNAL_ID,
            name=TEST_ORG_NAME,
            scopes="nvi:create",
            clients=[ClientCreate(name=TEST_CLIENT_NAME, scopes="nvi:read")],
        ),
        # mismatch in org client certs
        OrganizationCreate(
            external_id=TEST_EXTERNAL_ID,
            name=TEST_ORG_NAME,
            certificates=[CertificateCreate(organization_identifier=TEST_OIN, domain=TEST_DOMAIN)],
            clients=[
                ClientCreate(
                    name=TEST_CLIENT_NAME,
                    certificates=[CertificateCreate(organization_identifier=SECOND_OIN, domain=SECOND_DOMAIN)],
                )
            ],
        ),
        # mismatch org client sources
        OrganizationCreate(
            external_id=TEST_EXTERNAL_ID,
            name=TEST_ORG_NAME,
            sources=[SourceCreate(source_id=TEST_SOURCE_ID, name=TEST_SOURCE_NAME)],
            clients=[
                ClientCreate(
                    name=TEST_CLIENT_NAME, sources=[SourceCreate(source_id=SECOND_SOURCE_ID, name=SECOND_SOURCE_NAME)]
                )
            ],
        ),
    ],
)
def test_register_should_return_403(api: TestClient, body: OrganizationCreate) -> None:
    body.scopes = "some:scope"
    response = api.post("/organizations", json=body.model_dump())

    assert response.status_code == 403


@pytest.mark.parametrize(
    "org_1, org_2",
    [
        # same external id
        (
            OrganizationCreate(
                external_id=TEST_EXTERNAL_ID,
                name=TEST_ORG_NAME,
            ),
            OrganizationCreate(
                external_id=TEST_EXTERNAL_ID,
                name=SECOND_ORG_NAME,
            ),
        ),
        # same source id
        (
            OrganizationCreate(
                external_id=TEST_EXTERNAL_ID,
                name=TEST_ORG_NAME,
                sources=[SourceCreate(source_id=TEST_SOURCE_ID, name=TEST_SOURCE_NAME)],
            ),
            OrganizationCreate(
                external_id=SECOND_EXTERNAL_ID,
                name=SECOND_ORG_NAME,
                sources=[SourceCreate(source_id=TEST_SOURCE_ID, name=TEST_SOURCE_NAME)],
            ),
        ),
    ],
)
def test_register_should_return_409(
    api: TestClient,
    org_1: OrganizationCreate,
    org_2: OrganizationCreate,
) -> None:
    resp_1 = api.post("/organizations", json=org_1.model_dump())
    resp_2 = api.post("/organizations", json=org_2.model_dump())

    assert resp_1.status_code == 201
    assert resp_2.status_code == 409


@pytest.mark.parametrize(
    "body",
    [
        {"name": "Org"},  # missing external_id
        {"external_id": str(TEST_EXTERNAL_ID)},  # missing name
        {},  # missing everything
        {"external_id": str(TEST_EXTERNAL_ID), "name": ["not", "a", "string"]},  # wrong type
    ],
)
def test_register_invalid_body_returns_422(api: TestClient, body: dict[str, object]) -> None:
    response = api.post("/organizations", json=body)
    assert response.status_code == 422


def test_get_return_200(api: TestClient) -> None:
    data = {"external_id": str(TEST_EXTERNAL_ID), "name": "some name"}
    org = api.post("/organizations", json=data)
    result = org.json()
    assert "id" in result
    target = result["id"]

    resp = api.get(f"/organizations/{target}")

    assert resp.status_code == 200


def test_update_null_scopes_is_accepted(
    api: TestClient, organization_service: OrganizationService, org_create_dto_1: OrganizationCreate
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    response = api.put(
        f"/organizations/{str(org.id)}",
        json={"id": str(org.id), "name": org.name, "external_id": org.external_id.value, "scopes": None},
    )
    assert response.status_code == 200


def test_register_scopes_with_extra_whitespace_is_accepted(
    api: TestClient,
) -> None:
    response = api.post(
        "/organizations",
        json={"external_id": str(TEST_EXTERNAL_ID), "name": "Org", "scopes": "  nvi:read  nvi:create    "},
    )

    assert response.status_code == 201


def test_get_by_id_returns_200(
    api: TestClient, organization_service: OrganizationService, org_create_dto_1: OrganizationCreate
) -> None:
    entity = organization_service.create_one(org_create_dto_1)

    response = api.get(f"/organizations/{entity.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(entity.id)


def test_get_by_id_not_found_returns_404(api: TestClient) -> None:
    response = api.get(f"/organizations/{str(uuid4())}")
    assert response.status_code == 404


def test_get_by_id_invalid_uuid_returns_422(api: TestClient) -> None:
    response = api.get("/organizations/not-a-uuid")
    assert response.status_code == 422


def test_get_many_returns_list(
    api: TestClient,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
    org_create_dto_2: OrganizationCreate,
) -> None:
    organization_service.create_one(org_create_dto_1)
    organization_service.create_one(org_create_dto_2)
    response = api.get("/organizations")
    assert response.status_code == 200
    assert len(response.json()) == 2


@pytest.mark.parametrize(
    "query",
    [f"external_id={str(TEST_EXTERNAL_ID)}", "name=Acme", "scopes=read+write", "include_deleted=true"],
)
def test_get_many_passes_query_params(api: TestClient, query: str) -> None:
    resp = api.get(f"/organizations?{query}")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.parametrize("value", ["maybe", "2", "-1"])
def test_get_many_invalid_include_deleted_returns_422(api: TestClient, value: str) -> None:
    response = api.get(f"/organizations?include_deleted={value}")
    assert response.status_code == 422


def test_update_returns_200(
    api: TestClient, organization_service: OrganizationService, org_create_dto_1: OrganizationCreate
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    response = api.put(
        f"/organizations/{str(org.id)}", json={"name": "New Name", "external_id": SECOND_EXTERNAL_ID.value}
    )
    data = response.json()
    assert response.status_code == 200
    assert data["name"] == "New Name"
    assert data["external_id"] == SECOND_EXTERNAL_ID.value


def test_update_not_found_returns_404(api: TestClient, org_create_dto_1: OrganizationCreate) -> None:
    response = api.put(f"/organizations/{uuid4()}", json=org_create_dto_1.model_dump())
    assert response.status_code == 404


def test_update_invalid_uuid_returns_422(api: TestClient) -> None:
    response = api.put("/organizations/not-a-uuid", json={"name": "X"})
    assert response.status_code == 422


def test_delete_returns_204(
    api: TestClient, organization_service: OrganizationService, org_create_dto_1: OrganizationCreate
) -> None:
    org_create_dto_1.sources = None
    org_create_dto_1.certificates = None
    org_create_dto_1.clients = None
    org = organization_service.create_one(org_create_dto_1)
    response = api.delete(f"/organizations/{str(org.id)}")
    assert response.status_code == 204


def test_delete_returns_403(
    api: TestClient, organization_service: OrganizationService, org_create_dto_1: OrganizationCreate
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    response = api.delete(f"/organizations/{str(org.id)}")
    assert response.status_code == 403


def test_delete_not_found_returns_404(api: TestClient) -> None:
    response = api.delete(f"/organizations/{str(uuid4())}")
    assert response.status_code == 404


def test_delete_with_active_clients_returns_403(
    api: TestClient, organization_service: OrganizationService, org_create_dto_1: OrganizationCreate
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    response = api.delete(f"/organizations/{str(org.id)}")
    assert response.status_code == 403


def test_delete_invalid_uuid_returns_422(api: TestClient) -> None:
    response = api.delete("/organizations/not-a-uuid")
    assert response.status_code == 422
