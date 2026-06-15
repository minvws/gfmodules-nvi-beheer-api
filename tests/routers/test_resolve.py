from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from tests.conftest import VALID_OIN

RESOLVE = "/clients/resolve"


def _body(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {"oin": VALID_OIN, "common_name": "Client", "mandate_id": "mandate-1"}
    body.update(overrides)
    return body


@pytest.mark.parametrize("scopes", ["read write", "read", ""])
def test_resolve_returns_scopes(api: TestClient, mock_client_service: MagicMock, scopes: str) -> None:
    mock_client_service.resolve.return_value = scopes

    response = api.post(RESOLVE, json=_body())

    assert response.status_code == 200
    assert response.json() == scopes
    call = mock_client_service.resolve.call_args
    assert str(call.kwargs["oin"]) == VALID_OIN
    assert call.kwargs["common_name"] == "Client"
    assert call.kwargs["mandate_id"] == "mandate-1"


def test_resolve_unknown_client_returns_404(api: TestClient, mock_client_service: MagicMock) -> None:
    mock_client_service.resolve.return_value = None
    response = api.post(RESOLVE, json=_body())
    assert response.status_code == 404
    assert response.json()["detail"] == "Client not found."


@pytest.mark.parametrize(
    "body",
    [
        {"common_name": "C", "mandate_id": "m"},  # missing oin
        {"oin": VALID_OIN, "mandate_id": "m"},  # missing common_name
        {"oin": VALID_OIN, "common_name": "C"},  # missing mandate_id
        {"oin": "invalid-oin", "common_name": "C", "mandate_id": "m"},  # malformed oin
    ],
)
def test_resolve_invalid_body_returns_422(
    api: TestClient, mock_client_service: MagicMock, body: dict[str, object]
) -> None:
    response = api.post(RESOLVE, json=body)
    assert response.status_code == 422
    mock_client_service.resolve.assert_not_called()
