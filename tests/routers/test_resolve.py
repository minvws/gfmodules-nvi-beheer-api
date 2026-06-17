from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from tests.conftest import TEST_REGISTER_ID, VALID_OIN, make_client_entity

RESOLVE = "/clients/resolve"


def _body(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {"oin": str(VALID_OIN), "common_name": "Client", "org_ura": str(TEST_REGISTER_ID)}
    body.update(overrides)
    return body


@pytest.mark.parametrize("scopes", ["read write", "read", ""])
def test_resolve_returns_scopes_and_source_id(api: TestClient, mock_client_service: MagicMock, scopes: str) -> None:
    mock_client_service.resolve.return_value = make_client_entity(scopes=scopes, source_id="source-1")

    response = api.post(RESOLVE, json=_body())

    assert response.status_code == 200
    assert response.json() == {"scopes": scopes, "source_id": "source-1"}
    call = mock_client_service.resolve.call_args
    assert str(call.kwargs["oin"]) == str(VALID_OIN)
    assert call.kwargs["common_name"] == "Client"
    assert str(call.kwargs["org_ura"]) == str(TEST_REGISTER_ID)


def test_resolve_returns_no_source_id_when_absent(api: TestClient, mock_client_service: MagicMock) -> None:
    mock_client_service.resolve.return_value = make_client_entity(scopes="read", source_id=None)

    response = api.post(RESOLVE, json=_body())

    assert response.status_code == 200
    assert response.json() == {"scopes": "read"}


def test_resolve_unknown_client_returns_404(api: TestClient, mock_client_service: MagicMock) -> None:
    mock_client_service.resolve.return_value = None
    response = api.post(RESOLVE, json=_body())
    assert response.status_code == 404
    assert response.json()["detail"] == "Client not found."


def test_resolve_client_without_scopes_returns_404(api: TestClient, mock_client_service: MagicMock) -> None:
    mock_client_service.resolve.return_value = make_client_entity(scopes=None, source_id="source-1")
    response = api.post(RESOLVE, json=_body())
    assert response.status_code == 404
    assert response.json()["detail"] == "Client not found."


@pytest.mark.parametrize(
    "body",
    [
        {"common_name": "CN", "org_ura": str(TEST_REGISTER_ID)},  # missing oin
        {"oin": str(VALID_OIN), "org_ura": str(TEST_REGISTER_ID)},  # missing common_name
        {"oin": str(VALID_OIN), "common_name": "C"},  # missing org_ura
        {"oin": "invalid-oin", "common_name": "C", "org_ura": str(TEST_REGISTER_ID)},  # malformed oin
    ],
)
def test_resolve_invalid_body_returns_422(
    api: TestClient, mock_client_service: MagicMock, body: dict[str, object]
) -> None:
    response = api.post(RESOLVE, json=body)
    assert response.status_code == 422
    mock_client_service.resolve.assert_not_called()
