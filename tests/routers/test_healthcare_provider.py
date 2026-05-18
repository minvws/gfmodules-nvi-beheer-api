from typing import Any, Dict
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.models.healthcare_provider import Status


@pytest.fixture()
def test_provider_data() -> Dict[str, Any]:
    return {
        "ura_number": "00000123",
        "source_id": "source_1",
        "is_source": True,
        "is_viewer": True,
        "oin": "00000003123456780001",
        "common_name": "Test Provider",
        "status": Status.ACTIVE.value,
    }


def test_post_create_provider_success(client: TestClient, test_provider_data: Dict[str, Any]) -> None:
    response = client.post("/healthcare-providers", json=test_provider_data)

    assert response.status_code == 200
    data = response.json()
    assert data["ura_number"] == test_provider_data["ura_number"]
    assert data["source_id"] == test_provider_data["source_id"]
    assert data["common_name"] == test_provider_data["common_name"]
    assert "id" in data


def test_get_list_providers_empty(client: TestClient) -> None:
    response = client.get("/healthcare-providers")

    assert response.status_code == 200
    assert response.json() == []


def test_get_list_providers_with_data(client: TestClient, test_provider_data: Dict[str, Any]) -> None:
    client.post("/healthcare-providers", json=test_provider_data)
    response = client.get("/healthcare-providers")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["ura_number"] == test_provider_data["ura_number"]


@pytest.mark.parametrize(
    "query_params, expected_count",
    [
        ({"source_id": "source_1"}, 1),
        ({"source_id": "non_existent_source"}, 0),
        ({"ura_number": "00000123"}, 1),
        ({"ura_number": "00000456"}, 0),
        ({"status": [Status.ACTIVE.value]}, 1),
        ({"status": [Status.SUSPENDED.value]}, 0),
        ({"status": [Status.ACTIVE.value, Status.SOFT_FREEZE.value]}, 1),
        ({"oin": "00000003123456780001"}, 1),
        ({"oin": "00000003123456780002"}, 0),
    ],
)
def test_get_list_providers_with_query_params(
    client: TestClient, test_provider_data: Dict[str, Any], query_params: Dict[str, Any], expected_count: int
) -> None:
    client.post("/healthcare-providers", json=test_provider_data)
    response = client.get("/healthcare-providers", params=query_params)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == expected_count


def test_get_provider_by_id_success(client: TestClient, test_provider_data: Dict[str, Any]) -> None:
    create_response = client.post("/healthcare-providers", json=test_provider_data)
    provider_id = create_response.json()["id"]

    response = client.get(f"/healthcare-providers/{provider_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == provider_id
    assert data["common_name"] == test_provider_data["common_name"]


def test_get_provider_by_id_not_found(client: TestClient) -> None:
    response = client.get(f"/healthcare-providers/{uuid4()}")

    assert response.status_code == 404


def test_put_update_provider_success(client: TestClient, test_provider_data: Dict[str, Any]) -> None:
    create_response = client.post("/healthcare-providers", json=test_provider_data)
    provider_id = create_response.json()["id"]

    update_data = {**test_provider_data, "common_name": "Updated Provider"}
    response = client.put(f"/healthcare-providers/{provider_id}", json=update_data)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == provider_id
    assert data["common_name"] == "Updated Provider"


def test_put_update_provider_not_found(client: TestClient, test_provider_data: Dict[str, Any]) -> None:
    update_data = {**test_provider_data, "common_name": "Updated Provider"}
    response = client.put(f"/healthcare-providers/{uuid4()}", json=update_data)

    assert response.status_code == 404


def test_delete_provider_success(client: TestClient, test_provider_data: Dict[str, Any]) -> None:
    create_response = client.post("/healthcare-providers", json=test_provider_data)
    provider_id = create_response.json()["id"]

    response = client.delete(f"/healthcare-providers/{provider_id}")

    assert response.status_code == 204

    get_response = client.get(f"/healthcare-providers/{provider_id}")
    assert get_response.status_code == 404


def test_delete_provider_not_found(client: TestClient) -> None:
    response = client.delete(f"/healthcare-providers/{uuid4()}")

    assert response.status_code == 404
