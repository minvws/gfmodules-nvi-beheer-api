from unittest.mock import MagicMock
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from tests.conftest import VALID_OIN, make_organization_entity

ORG_ID = "11111111-1111-1111-1111-111111111111"


@pytest.mark.parametrize("scopes", [None, "read write"])
def test_register_returns_201(api: TestClient, mock_organization_service: MagicMock, scopes: str | None) -> None:
    entity = make_organization_entity(register_id=VALID_OIN, name="Org", scopes=scopes)
    mock_organization_service.create_one.return_value = entity

    body: dict[str, object] = {"register_id": VALID_OIN, "name": "Org"}
    if scopes is not None:
        body["scopes"] = scopes
    response = api.post("/organizations", json=body)

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == str(entity.id)
    assert data["register_id"] == VALID_OIN
    assert data["name"] == "Org"
    mock_organization_service.create_one.assert_called_once_with(register_id=VALID_OIN, name="Org", scopes=scopes)


def test_register_conflict_returns_409(api: TestClient, mock_organization_service: MagicMock) -> None:
    mock_organization_service.create_one.side_effect = IntegrityError("stmt", {}, Exception("duplicate"))
    response = api.post("/organizations", json={"register_id": VALID_OIN, "name": "Org"})
    assert response.status_code == 409


@pytest.mark.parametrize(
    "body",
    [
        {"name": "Org"},  # missing register_id
        {"register_id": VALID_OIN},  # missing name
        {},  # missing everything
        {"register_id": VALID_OIN, "name": ["not", "a", "string"]},  # wrong type
    ],
)
def test_register_invalid_body_returns_422(
    api: TestClient, mock_organization_service: MagicMock, body: dict[str, object]
) -> None:
    response = api.post("/organizations", json=body)
    assert response.status_code == 422
    mock_organization_service.create_one.assert_not_called()


def test_get_by_id_returns_200(api: TestClient, mock_organization_service: MagicMock) -> None:
    entity = make_organization_entity()
    mock_organization_service.get_one.return_value = entity

    response = api.get(f"/organizations/{entity.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(entity.id)
    mock_organization_service.get_one.assert_called_once_with(entity.id)


def test_get_by_id_not_found_returns_404(api: TestClient, mock_organization_service: MagicMock) -> None:
    mock_organization_service.get_one.return_value = None
    response = api.get(f"/organizations/{ORG_ID}")
    assert response.status_code == 404


def test_get_by_id_invalid_uuid_returns_422(api: TestClient) -> None:
    response = api.get("/organizations/not-a-uuid")
    assert response.status_code == 422


@pytest.mark.parametrize("count", [0, 1, 3])
def test_get_many_returns_list(api: TestClient, mock_organization_service: MagicMock, count: int) -> None:
    mock_organization_service.get_many.return_value = [make_organization_entity(name=f"Org {i}") for i in range(count)]
    response = api.get("/organizations")
    assert response.status_code == 200
    assert len(response.json()) == count


def test_get_many_without_params_uses_defaults(api: TestClient, mock_organization_service: MagicMock) -> None:
    mock_organization_service.get_many.return_value = []
    api.get("/organizations")
    mock_organization_service.get_many.assert_called_once_with(
        register_id=None, name=None, scopes=None, include_deleted=False
    )


@pytest.mark.parametrize(
    "query, expected",
    [
        ("register_id=reg-1", {"register_id": "reg-1", "name": None, "scopes": None, "include_deleted": False}),
        ("name=Acme", {"register_id": None, "name": "Acme", "scopes": None, "include_deleted": False}),
        ("scopes=read+write", {"register_id": None, "name": None, "scopes": "read write", "include_deleted": False}),
        ("include_deleted=true", {"register_id": None, "name": None, "scopes": None, "include_deleted": True}),
    ],
)
def test_get_many_passes_query_params(
    api: TestClient, mock_organization_service: MagicMock, query: str, expected: dict[str, object]
) -> None:
    mock_organization_service.get_many.return_value = []
    api.get(f"/organizations?{query}")
    mock_organization_service.get_many.assert_called_once_with(**expected)


@pytest.mark.parametrize("value", ["maybe", "2", "-1"])
def test_get_many_invalid_include_deleted_returns_422(api: TestClient, value: str) -> None:
    response = api.get(f"/organizations?include_deleted={value}")
    assert response.status_code == 422


def test_update_returns_200(api: TestClient, mock_organization_service: MagicMock) -> None:
    entity = make_organization_entity(name="New Name")
    mock_organization_service.update_one.return_value = entity
    response = api.put(f"/organizations/{entity.id}", json={"name": "New Name"})
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"


def test_update_not_found_returns_404(api: TestClient, mock_organization_service: MagicMock) -> None:
    mock_organization_service.update_one.return_value = None
    response = api.put(f"/organizations/{ORG_ID}", json={"name": "X"})
    assert response.status_code == 404


@pytest.mark.parametrize(
    "body, expected_kwargs",
    [
        ({"name": "N"}, {"name": "N"}),
        ({"scopes": "read"}, {"scopes": "read"}),
        ({"name": "N", "scopes": "read"}, {"name": "N", "scopes": "read"}),
        ({}, {}),  # nothing supplied -> nothing forwarded
    ],
)
def test_update_forwards_only_supplied_fields(
    api: TestClient, mock_organization_service: MagicMock, body: dict[str, object], expected_kwargs: dict[str, object]
) -> None:
    mock_organization_service.update_one.return_value = make_organization_entity()
    api.put(f"/organizations/{ORG_ID}", json=body)
    mock_organization_service.update_one.assert_called_once_with(UUID(ORG_ID), **expected_kwargs)


def test_update_invalid_uuid_returns_422(api: TestClient) -> None:
    response = api.put("/organizations/not-a-uuid", json={"name": "X"})
    assert response.status_code == 422


def test_delete_returns_204(api: TestClient, mock_organization_service: MagicMock) -> None:
    mock_organization_service.delete_one.return_value = make_organization_entity()
    response = api.delete(f"/organizations/{ORG_ID}")
    assert response.status_code == 204
    assert response.content == b""
    mock_organization_service.delete_one.assert_called_once_with(UUID(ORG_ID))


def test_delete_not_found_returns_404(api: TestClient, mock_organization_service: MagicMock) -> None:
    mock_organization_service.delete_one.return_value = None
    response = api.delete(f"/organizations/{ORG_ID}")
    assert response.status_code == 404


def test_delete_invalid_uuid_returns_422(api: TestClient) -> None:
    response = api.delete("/organizations/not-a-uuid")
    assert response.status_code == 422
