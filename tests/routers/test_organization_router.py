from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.models.client import ClientCreate
from app.models.oin import Oin
from app.models.organization import Organization, OrganizationCreate
from app.models.scopes import AuthorizationScope
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
    TEST_SCOPES,
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
        # mismatch in org client scope
        OrganizationCreate(
            external_id=TEST_EXTERNAL_ID,
            name=TEST_ORG_NAME,
            scopes=[AuthorizationScope("nvi:create")],
            clients=[ClientCreate(name=TEST_CLIENT_NAME, scopes=[AuthorizationScope("nvi:read")])],
        ),
    ],
)
def test_register_should_return_403(api: TestClient, body: OrganizationCreate) -> None:
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


def test_register_should_allow_certificate_used_by_another_organization(api: TestClient) -> None:
    first_body = {
        "external_id": str(TEST_EXTERNAL_ID),
        "name": TEST_ORG_NAME,
        "certificates": [{"organization_identifier": str(TEST_OIN), "domain": TEST_DOMAIN}],
    }
    second_body = {**first_body, "external_id": str(SECOND_EXTERNAL_ID), "name": SECOND_ORG_NAME}

    first_response = api.post("/organizations", json=first_body)
    second_response = api.post("/organizations", json=second_body)

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    first = first_response.json()
    second = second_response.json()
    assert first["id"] != second["id"]
    assert first["certificates"][0]["id"] != second["certificates"][0]["id"]
    assert (
        first["certificates"][0]["organization_identifier"]
        == second["certificates"][0]["organization_identifier"]
        == str(TEST_OIN)
    )
    assert first["certificates"][0]["domain"] == second["certificates"][0]["domain"] == TEST_DOMAIN


def test_register_should_return_422_when_certificates_are_duplicated(api: TestClient) -> None:
    body = {
        "external_id": str(TEST_EXTERNAL_ID),
        "name": TEST_ORG_NAME,
        "certificates": [
            {"organization_identifier": str(TEST_OIN), "domain": TEST_DOMAIN},
            {"organization_identifier": str(TEST_OIN), "domain": TEST_DOMAIN},
        ],
    }

    response = api.post("/organizations", json=body)

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert len(errors) == 1
    assert errors[0]["loc"] == ["body", "certificates"]
    assert errors[0]["type"] == "value_error"
    assert errors[0]["msg"] == f"Value error, Duplicate certificate values: {TEST_OIN}/{TEST_DOMAIN}"
    assert api.get("/organizations").json() == []


def test_register_should_return_422_when_client_certificates_are_duplicated(api: TestClient) -> None:
    body = {
        "external_id": str(TEST_EXTERNAL_ID),
        "name": TEST_ORG_NAME,
        "certificates": [{"organization_identifier": str(TEST_OIN), "domain": TEST_DOMAIN}],
        "clients": [
            {"name": "First client"},
            {
                "name": "Second client",
                "certificates": [
                    {"organization_identifier": str(TEST_OIN), "domain": TEST_DOMAIN},
                    {"organization_identifier": str(TEST_OIN), "domain": TEST_DOMAIN},
                ],
            },
        ],
    }

    response = api.post("/organizations", json=body)

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert len(errors) == 1
    assert errors[0]["loc"] == ["body", "clients", 1, "certificates"]
    assert errors[0]["type"] == "value_error"
    assert errors[0]["msg"] == f"Value error, Duplicate certificate values: {TEST_OIN}/{TEST_DOMAIN}"
    assert api.get("/organizations").json() == []


@pytest.mark.parametrize(
    "organization_pairs, client_pairs, unknown_values",
    [
        (None, [(TEST_OIN, TEST_DOMAIN)], f"{TEST_OIN}/{TEST_DOMAIN}"),
        ([], [(TEST_OIN, TEST_DOMAIN)], f"{TEST_OIN}/{TEST_DOMAIN}"),
        ([(TEST_OIN, TEST_DOMAIN)], [(SECOND_OIN, SECOND_DOMAIN)], f"{SECOND_OIN}/{SECOND_DOMAIN}"),
        (
            [(TEST_OIN, TEST_DOMAIN), (SECOND_OIN, SECOND_DOMAIN)],
            [(TEST_OIN, SECOND_DOMAIN)],
            f"{TEST_OIN}/{SECOND_DOMAIN}",
        ),
        (
            [(TEST_OIN, TEST_DOMAIN), (SECOND_OIN, SECOND_DOMAIN)],
            [(TEST_OIN, TEST_DOMAIN), (TEST_OIN, SECOND_DOMAIN)],
            f"{TEST_OIN}/{SECOND_DOMAIN}",
        ),
    ],
)
def test_register_should_return_422_when_client_certificates_are_unknown(
    api: TestClient,
    organization_pairs: list[tuple[Oin, str]] | None,
    client_pairs: list[tuple[Oin, str]],
    unknown_values: str,
) -> None:
    body: dict[str, object] = {
        "external_id": str(TEST_EXTERNAL_ID),
        "name": TEST_ORG_NAME,
        "clients": [
            {"name": "First client"},
            {
                "name": "Second client",
                "certificates": [
                    {"organization_identifier": str(identifier), "domain": domain}
                    for identifier, domain in client_pairs
                ],
            },
        ],
    }
    if organization_pairs is not None:
        body["certificates"] = [
            {"organization_identifier": str(identifier), "domain": domain} for identifier, domain in organization_pairs
        ]

    response = api.post("/organizations", json=body)

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert len(errors) == 1
    assert errors[0]["loc"] == ["body"]
    assert errors[0]["type"] == "value_error"
    assert errors[0]["msg"] == f"Value error, Client 1 has unknown certificate values: {unknown_values}"
    assert api.get("/organizations").json() == []


@pytest.mark.parametrize("client_count", [1, 2])
def test_register_should_allow_clients_to_select_an_organization_certificate_subset(
    api: TestClient, client_count: int
) -> None:
    body = {
        "external_id": str(TEST_EXTERNAL_ID),
        "name": TEST_ORG_NAME,
        "certificates": [
            {"organization_identifier": str(TEST_OIN), "domain": TEST_DOMAIN},
            {"organization_identifier": str(SECOND_OIN), "domain": SECOND_DOMAIN},
        ],
        "clients": [
            {
                "name": f"Client {index}",
                "certificates": [{"organization_identifier": str(TEST_OIN), "domain": TEST_DOMAIN}],
            }
            for index in range(client_count)
        ],
    }

    response = api.post("/organizations", json=body)

    assert response.status_code == 201
    result = response.json()
    assert len(result["certificates"]) == 2
    assert len(result["clients"]) == client_count
    for client in result["clients"]:
        assert client["certificates"] == [result["certificates"][0]]


def test_register_should_allow_source_id_used_by_another_organization(api: TestClient) -> None:
    org_1 = OrganizationCreate(
        external_id=TEST_EXTERNAL_ID,
        name=TEST_ORG_NAME,
        sources=[SourceCreate(source_id=TEST_SOURCE_ID, name=TEST_SOURCE_NAME)],
    )
    org_2 = OrganizationCreate(
        external_id=SECOND_EXTERNAL_ID,
        name=SECOND_ORG_NAME,
        sources=[SourceCreate(source_id=TEST_SOURCE_ID, name=SECOND_SOURCE_NAME)],
    )

    resp_1 = api.post("/organizations", json=org_1.model_dump())
    resp_2 = api.post("/organizations", json=org_2.model_dump())

    assert resp_1.status_code == 201
    assert resp_2.status_code == 201
    result_1 = resp_1.json()
    result_2 = resp_2.json()
    source_1 = result_1["sources"][0]
    source_2 = result_2["sources"][0]

    assert result_1["id"] != result_2["id"]
    assert source_1["source_id"] == source_2["source_id"] == TEST_SOURCE_ID
    assert source_1["id"] != source_2["id"]
    assert source_1["organization_id"] == result_1["id"]
    assert source_2["organization_id"] == result_2["id"]


def test_register_should_return_422_when_source_ids_are_duplicated_in_payload(api: TestClient) -> None:
    body = {
        "external_id": str(TEST_EXTERNAL_ID),
        "name": TEST_ORG_NAME,
        "sources": [
            {"source_id": TEST_SOURCE_ID, "name": TEST_SOURCE_NAME},
            {"source_id": TEST_SOURCE_ID, "name": SECOND_SOURCE_NAME},
        ],
    }

    response = api.post("/organizations", json=body)

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert len(errors) == 1
    assert errors[0]["loc"] == ["body", "sources"]
    assert errors[0]["type"] == "value_error"
    assert errors[0]["msg"] == f"Value error, Duplicate source_id values: {TEST_SOURCE_ID}"
    assert api.get("/organizations").json() == []


def test_register_should_return_422_when_client_source_ids_are_duplicated(api: TestClient) -> None:
    body = {
        "external_id": str(TEST_EXTERNAL_ID),
        "name": TEST_ORG_NAME,
        "sources": [{"source_id": TEST_SOURCE_ID, "name": TEST_SOURCE_NAME}],
        "clients": [
            {"name": "First client"},
            {
                "name": "Second client",
                "sources": [
                    {"source_id": TEST_SOURCE_ID, "name": TEST_SOURCE_NAME},
                    {"source_id": TEST_SOURCE_ID, "name": SECOND_SOURCE_NAME},
                ],
            },
        ],
    }

    response = api.post("/organizations", json=body)

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert len(errors) == 1
    assert errors[0]["loc"] == ["body", "clients", 1, "sources"]
    assert errors[0]["type"] == "value_error"
    assert errors[0]["msg"] == f"Value error, Duplicate source_id values: {TEST_SOURCE_ID}"
    assert api.get("/organizations").json() == []


@pytest.mark.parametrize(
    "organization_source_ids, client_source_ids, unknown_ids",
    [
        (None, ["unknown"], "unknown"),
        ([], ["unknown"], "unknown"),
        ([TEST_SOURCE_ID], ["unknown"], "unknown"),
        ([TEST_SOURCE_ID, SECOND_SOURCE_ID], [TEST_SOURCE_ID, "unknown-2", "unknown-1"], "unknown-2 unknown-1"),
    ],
)
def test_register_should_return_422_when_client_sources_are_unknown(
    api: TestClient, organization_source_ids: list[str] | None, client_source_ids: list[str], unknown_ids: str
) -> None:
    body: dict[str, object] = {
        "external_id": str(TEST_EXTERNAL_ID),
        "name": TEST_ORG_NAME,
        "clients": [
            {"name": "First client"},
            {
                "name": "Second client",
                "sources": [{"source_id": source_id, "name": "Reference"} for source_id in client_source_ids],
            },
        ],
    }
    if organization_source_ids is not None:
        body["sources"] = [
            {"source_id": source_id, "name": "Organization source"} for source_id in organization_source_ids
        ]

    response = api.post("/organizations", json=body)

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert len(errors) == 1
    assert errors[0]["loc"] == ["body"]
    assert errors[0]["type"] == "value_error"
    assert errors[0]["msg"] == f"Value error, Client 1 has unknown source_id values: {unknown_ids}"
    assert api.get("/organizations").json() == []


@pytest.mark.parametrize("client_count", [1, 2])
def test_register_should_allow_clients_to_select_an_organization_source_subset(
    api: TestClient, client_count: int
) -> None:
    body = {
        "external_id": str(TEST_EXTERNAL_ID),
        "name": TEST_ORG_NAME,
        "sources": [
            {"source_id": TEST_SOURCE_ID, "name": TEST_SOURCE_NAME},
            {"source_id": SECOND_SOURCE_ID, "name": SECOND_SOURCE_NAME},
        ],
        "clients": [
            {"name": f"Client {index}", "sources": [{"source_id": TEST_SOURCE_ID, "name": "Reference"}]}
            for index in range(client_count)
        ],
    }

    response = api.post("/organizations", json=body)

    assert response.status_code == 201
    result = response.json()
    assert len(result["sources"]) == 2
    assert len(result["clients"]) == client_count
    for client in result["clients"]:
        assert client["sources"] == [result["sources"][0]]


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
    org_create_dto_1.clients = None
    org = organization_service.create_one(org_create_dto_1)
    response = api.put(
        f"/organizations/{org.id!s}",
        json={"id": str(org.id), "name": org.name, "external_id": org.external_id.value, "scopes": None},
    )
    assert response.status_code == 200


def test_get_by_id_returns_200(
    api: TestClient, organization_service: OrganizationService, org_create_dto_1: OrganizationCreate
) -> None:
    entity = organization_service.create_one(org_create_dto_1)

    response = api.get(f"/organizations/{entity.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(entity.id)


def test_get_by_id_not_found_returns_404(api: TestClient) -> None:
    response = api.get(f"/organizations/{uuid4()!s}")
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


@pytest.fixture
def two_orgs(
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
    org_create_dto_2: OrganizationCreate,
) -> tuple[Organization, Organization]:
    """Two organizations that differ on every filterable field (see org_create_dto_1/2 in conftest).

    first:  all scopes; certs (TEST_OIN, TEST_DOMAIN) + (SECOND_OIN, SECOND_DOMAIN); sources source-001/002;
            client "Test Client" (nvi:create, nvi:read) with cert TEST_OIN and both sources
    second: nvi:create + nvi:localize; cert (SECOND_OIN, SECOND_DOMAIN); source source-3;
            client "Test Client 2" (nvi:localize) with source source-3 and no certificates
    """
    return organization_service.create_one(org_create_dto_1), organization_service.create_one(org_create_dto_2)


def org_ids(response_json: list[dict[str, Any]]) -> list[str]:
    return sorted(o["id"] for o in response_json)


@pytest.mark.parametrize(
    "query, expected",
    [
        ("", ["first", "second"]),
        (f"external_id={TEST_EXTERNAL_ID!s}", ["first"]),
        (f"external_id={SECOND_EXTERNAL_ID!s}", ["second"]),
        (f"name={TEST_ORG_NAME}", ["first"]),
        ("name=Unknown", []),
        ("scopes=nvi:read", ["first"]),
        ("scopes=nvi:localize", ["first", "second"]),
        ("scopes=nvi:read&scopes=nvi:localize", ["first", "second"]),
        (f"cert_identifier={TEST_OIN!s}", ["first"]),
        (f"cert_identifier={SECOND_OIN!s}", ["first", "second"]),
        (f"cert_domain={SECOND_DOMAIN}", ["first", "second"]),
        # identifier and domain must match on the same certificate
        (f"cert_identifier={TEST_OIN!s}&cert_domain={SECOND_DOMAIN}", []),
        ("source_id=source-3", ["second"]),
        (f"source_name={TEST_SOURCE_NAME}", ["first"]),
        (f"client_name={TEST_CLIENT_NAME}", ["first"]),
        ("client_name=Test Client 2", ["second"]),
        ("client_scopes=nvi:read", ["first"]),
        ("client_scopes=nvi:localize", ["second"]),
        (f"client_cert_identifier={TEST_OIN!s}", ["first"]),
        # SECOND_DOMAIN belongs to both organizations, but no client has it assigned
        (f"client_cert_domain={SECOND_DOMAIN}", []),
        ("client_source_id=source-3", ["second"]),
        (f"client_source_name={SECOND_SOURCE_NAME}", ["first"]),
        (f"name={TEST_ORG_NAME}&source_id=source-3", []),
        (f"name={SECOND_ORG_NAME}&source_id=source-3", ["second"]),
    ],
)
def test_get_many_applies_query_params(
    api: TestClient, two_orgs: tuple[Organization, Organization], query: str, expected: list[str]
) -> None:
    first, second = two_orgs
    by_label = {"first": str(first.id), "second": str(second.id)}

    response = api.get(f"/organizations?{query}")

    assert response.status_code == 200
    assert org_ids(response.json()) == sorted(by_label[label] for label in expected)


def test_get_many_filters_on_cert_id(api: TestClient, two_orgs: tuple[Organization, Organization]) -> None:
    _, second = two_orgs
    assert second.certificates is not None

    response = api.get(f"/organizations?cert_id={second.certificates[0].id}")

    assert response.status_code == 200
    assert org_ids(response.json()) == [str(second.id)]


def test_get_many_hides_soft_deleted_organizations(
    api: TestClient, two_orgs: tuple[Organization, Organization]
) -> None:
    first, second = two_orgs
    deleted = api.post("/organizations", json={"external_id": "11223344", "name": "Deleted Org"}).json()
    assert api.delete(f"/organizations/{deleted['id']}").status_code == 204
    active = sorted([str(first.id), str(second.id)])

    assert org_ids(api.get("/organizations").json()) == active
    assert org_ids(api.get("/organizations?include_deleted=false").json()) == active
    assert org_ids(api.get("/organizations?include_deleted=true").json()) == sorted([*active, deleted["id"]])
    assert api.get("/organizations?name=Deleted Org").json() == []
    assert org_ids(api.get("/organizations?name=Deleted Org&include_deleted=true").json()) == [deleted["id"]]


def test_get_many_ignores_soft_deleted_certificates_when_filtering(
    api: TestClient, two_orgs: tuple[Organization, Organization]
) -> None:
    first, second = two_orgs
    assert second.certificates is not None
    cert = second.certificates[0]
    assert api.delete(f"/organizations/{second.id}/certificate/{cert.id}").status_code == 200
    query = f"/organizations?cert_identifier={SECOND_OIN!s}"

    assert org_ids(api.get(query).json()) == [str(first.id)]
    assert org_ids(api.get(f"{query}&include_deleted=true").json()) == sorted([str(first.id), str(second.id)])
    listed_second = next(o for o in api.get("/organizations").json() if o["id"] == str(second.id))
    assert "certificates" not in listed_second


def test_get_many_unknown_query_param_returns_422(api: TestClient) -> None:
    response = api.get("/organizations?unknown=value")

    assert response.status_code == 422


@pytest.mark.parametrize("value", ["maybe", "2", "-1"])
def test_get_many_invalid_include_deleted_returns_422(api: TestClient, value: str) -> None:
    response = api.get(f"/organizations?include_deleted={value}")
    assert response.status_code == 422


def test_update_returns_200(
    api: TestClient, organization_service: OrganizationService, org_create_dto_1: OrganizationCreate
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    response = api.put(
        f"/organizations/{org.id!s}",
        json={"name": "New Name", "external_id": SECOND_EXTERNAL_ID.value, "scopes": TEST_SCOPES},
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
    response = api.delete(f"/organizations/{org.id!s}")
    assert response.status_code == 204


def test_delete_returns_409(
    api: TestClient, organization_service: OrganizationService, org_create_dto_1: OrganizationCreate
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    response = api.delete(f"/organizations/{org.id!s}")
    assert response.status_code == 409


def test_delete_not_found_returns_404(api: TestClient) -> None:
    response = api.delete(f"/organizations/{uuid4()!s}")
    assert response.status_code == 404


def test_delete_with_active_clients_returns_409(
    api: TestClient, organization_service: OrganizationService, org_create_dto_1: OrganizationCreate
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    response = api.delete(f"/organizations/{org.id!s}")
    assert response.status_code == 409


def test_delete_invalid_uuid_returns_422(api: TestClient) -> None:
    response = api.delete("/organizations/not-a-uuid")
    assert response.status_code == 422
