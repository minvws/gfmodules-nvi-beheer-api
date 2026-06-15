from unittest.mock import MagicMock
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.services.exceptions import ScopesNotGrantedError
from tests.conftest import VALID_OIN, make_client_entity

ORG_ID = "11111111-1111-1111-1111-111111111111"
CLIENT_ID = "22222222-2222-2222-2222-222222222222"
BASE = f"/organizations/{ORG_ID}/clients"


def _create_body(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {"oin": VALID_OIN, "common_name": "Client", "mandate_id": "mandate-1"}
    body.update(overrides)
    return body


@pytest.mark.parametrize(
    "method, path, body",
    [
        ("post", BASE, {"oin": VALID_OIN, "common_name": "C", "mandate_id": "m"}),
        ("get", f"{BASE}/{CLIENT_ID}", None),
        ("get", BASE, None),
        ("put", f"{BASE}/{CLIENT_ID}", {"common_name": "C"}),
        ("delete", f"{BASE}/{CLIENT_ID}", None),
    ],
)
def test_returns_404_when_organization_missing(
    api: TestClient,
    mock_organization_service: MagicMock,
    method: str,
    path: str,
    body: dict[str, object] | None,
) -> None:
    mock_organization_service.exists.return_value = False
    response = api.request(method, path, json=body)
    assert response.status_code == 404
    assert response.json()["detail"] == "Organization not found."


@pytest.mark.parametrize("scopes", [None, "read"])
def test_register_returns_201(api: TestClient, mock_client_service: MagicMock, scopes: str | None) -> None:
    entity = make_client_entity(organization_id=UUID(ORG_ID), scopes=scopes)
    mock_client_service.create_one.return_value = entity

    response = api.post(BASE, json=_create_body(**({"scopes": scopes} if scopes is not None else {})))

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == str(entity.id)
    assert data["oin"] == VALID_OIN
    assert data["mandate_id"] == "mandate-1"

    call = mock_client_service.create_one.call_args
    assert call.kwargs["organization_id"] == UUID(ORG_ID)
    assert str(call.kwargs["oin"]) == VALID_OIN
    assert call.kwargs["common_name"] == "Client"
    assert call.kwargs["mandate_id"] == "mandate-1"
    assert call.kwargs["scopes"] == scopes


def test_register_ungranted_scope_returns_422(api: TestClient, mock_client_service: MagicMock) -> None:
    mock_client_service.create_one.side_effect = ScopesNotGrantedError({"write"})
    response = api.post(BASE, json=_create_body(scopes="read write"))
    assert response.status_code == 422


def test_register_conflict_returns_409(api: TestClient, mock_client_service: MagicMock) -> None:
    mock_client_service.create_one.side_effect = IntegrityError("stmt", {}, Exception("duplicate"))
    response = api.post(BASE, json=_create_body())
    assert response.status_code == 409


@pytest.mark.parametrize(
    "body",
    [
        {"common_name": "C", "mandate_id": "m"},  # missing oin
        {"oin": VALID_OIN, "mandate_id": "m"},  # missing common_name
        {"oin": VALID_OIN, "common_name": "C"},  # missing mandate_id
        {"oin": "invalid-oin", "common_name": "C", "mandate_id": "m"},  # malformed oin
    ],
)
def test_register_invalid_body_returns_422(
    api: TestClient, mock_client_service: MagicMock, body: dict[str, object]
) -> None:
    response = api.post(BASE, json=body)
    assert response.status_code == 422
    mock_client_service.create_one.assert_not_called()


def test_get_by_id_returns_200(api: TestClient, mock_client_service: MagicMock) -> None:
    entity = make_client_entity(organization_id=UUID(ORG_ID))
    mock_client_service.get_one.return_value = entity

    response = api.get(f"{BASE}/{entity.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(entity.id)
    mock_client_service.get_one.assert_called_once_with(entity.id, UUID(ORG_ID))


def test_get_by_id_not_found_returns_404(api: TestClient, mock_client_service: MagicMock) -> None:
    mock_client_service.get_one.return_value = None
    response = api.get(f"{BASE}/{CLIENT_ID}")
    assert response.status_code == 404


@pytest.mark.parametrize(
    "path",
    [
        f"/organizations/not-a-uuid/clients/{CLIENT_ID}",  # bad organization_id
        f"{BASE}/not-a-uuid",  # bad client id
    ],
)
def test_get_by_id_invalid_uuid_returns_422(api: TestClient, path: str) -> None:
    response = api.get(path)
    assert response.status_code == 422


@pytest.mark.parametrize("count", [0, 2])
def test_get_many_returns_list(api: TestClient, mock_client_service: MagicMock, count: int) -> None:
    mock_client_service.get_many.return_value = [
        make_client_entity(organization_id=UUID(ORG_ID), mandate_id=f"m-{i}") for i in range(count)
    ]
    response = api.get(BASE)
    assert response.status_code == 200
    assert len(response.json()) == count


def test_get_many_without_params_uses_defaults(api: TestClient, mock_client_service: MagicMock) -> None:
    mock_client_service.get_many.return_value = []
    api.get(BASE)
    mock_client_service.get_many.assert_called_once_with(
        organization_id=UUID(ORG_ID),
        oin=None,
        common_name=None,
        mandate_id=None,
        scopes=None,
        include_deleted=False,
    )


def test_get_many_passes_query_params(api: TestClient, mock_client_service: MagicMock) -> None:
    mock_client_service.get_many.return_value = []
    api.get(f"{BASE}?oin={VALID_OIN}&common_name=CN-1&mandate_id=m-1&scopes=read+write&include_deleted=true")

    call = mock_client_service.get_many.call_args
    assert call.kwargs["organization_id"] == UUID(ORG_ID)
    assert str(call.kwargs["oin"]) == VALID_OIN
    assert call.kwargs["common_name"] == "CN-1"
    assert call.kwargs["mandate_id"] == "m-1"
    assert call.kwargs["scopes"] == "read write"
    assert call.kwargs["include_deleted"] is True


@pytest.mark.parametrize("query", ["oin=invalid-oin", "include_deleted=maybe"])
def test_get_many_invalid_query_returns_422(api: TestClient, query: str) -> None:
    response = api.get(f"{BASE}?{query}")
    assert response.status_code == 422


def test_update_returns_200(api: TestClient, mock_client_service: MagicMock) -> None:
    entity = make_client_entity(organization_id=UUID(ORG_ID), common_name="Updated")
    mock_client_service.update_one.return_value = entity
    response = api.put(f"{BASE}/{entity.id}", json={"common_name": "Updated"})
    assert response.status_code == 200
    assert response.json()["common_name"] == "Updated"


def test_update_not_found_returns_404(api: TestClient, mock_client_service: MagicMock) -> None:
    mock_client_service.update_one.return_value = None
    response = api.put(f"{BASE}/{CLIENT_ID}", json={"common_name": "X"})
    assert response.status_code == 404


def test_update_ungranted_scope_returns_422(api: TestClient, mock_client_service: MagicMock) -> None:
    mock_client_service.update_one.side_effect = ScopesNotGrantedError({"write"})
    response = api.put(f"{BASE}/{CLIENT_ID}", json={"scopes": "read write"})
    assert response.status_code == 422


@pytest.mark.parametrize(
    "body, expected_kwargs",
    [
        ({"common_name": "N"}, {"common_name": "N"}),
        ({"scopes": "read"}, {"scopes": "read"}),
        ({"mandate_id": "m-2", "common_name": "N"}, {"mandate_id": "m-2", "common_name": "N"}),
        ({}, {}),  # nothing supplied -> nothing forwarded
    ],
)
def test_update_forwards_only_supplied_fields(
    api: TestClient, mock_client_service: MagicMock, body: dict[str, object], expected_kwargs: dict[str, object]
) -> None:
    mock_client_service.update_one.return_value = make_client_entity(organization_id=UUID(ORG_ID))
    api.put(f"{BASE}/{CLIENT_ID}", json=body)
    mock_client_service.update_one.assert_called_once_with(UUID(CLIENT_ID), UUID(ORG_ID), **expected_kwargs)


def test_delete_returns_204(api: TestClient, mock_client_service: MagicMock) -> None:
    mock_client_service.delete_one.return_value = make_client_entity(organization_id=UUID(ORG_ID))
    response = api.delete(f"{BASE}/{CLIENT_ID}")
    assert response.status_code == 204
    assert response.content == b""
    mock_client_service.delete_one.assert_called_once_with(UUID(CLIENT_ID), UUID(ORG_ID))


def test_delete_not_found_returns_404(api: TestClient, mock_client_service: MagicMock) -> None:
    mock_client_service.delete_one.return_value = None
    response = api.delete(f"{BASE}/{CLIENT_ID}")
    assert response.status_code == 404
