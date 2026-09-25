from datetime import datetime as now
from typing import Any, Generator
from uuid import uuid4

import inject
import pytest
from pydantic import ValidationError

from app.models.organization import Organization, OrganizationCreate, OrganizationUpdate
from tests.conftest import TEST_EXTERNAL_ID, TEST_ORG_NAME


@pytest.fixture(autouse=True)
def configure_allowed_scopes() -> Generator[Any, Any, Any]:
    inject.clear_and_configure(lambda binder: binder.bind("allowed_scopes", {"read", "write"}))
    yield
    inject.clear()


def test_create_should_succeed() -> None:
    model = OrganizationCreate(external_id=TEST_EXTERNAL_ID, name=TEST_ORG_NAME)
    assert str(model.external_id) == str(TEST_EXTERNAL_ID)
    assert model.name == TEST_ORG_NAME
    assert model.scopes is None


def test_create_with_scopes_should_succeed() -> None:
    model = OrganizationCreate(external_id=TEST_EXTERNAL_ID, name=TEST_ORG_NAME, scopes="read write")
    assert model.scopes == "read write"


def test_create_missing_external_id_should_raise() -> None:
    with pytest.raises(ValidationError):
        OrganizationCreate(name=TEST_ORG_NAME)  # type: ignore[call-arg]


def test_create_missing_name_should_raise() -> None:
    with pytest.raises(ValidationError):
        OrganizationCreate(external_id=TEST_EXTERNAL_ID)  # type: ignore


def test_update_should_succeed() -> None:
    model = OrganizationUpdate(name="New Name", external_id=TEST_EXTERNAL_ID)
    assert model.name == "New Name"
    assert model.external_id == TEST_EXTERNAL_ID
    assert model.scopes is None
    assert model.certificates is None
    assert model.sources is None


def test_update_only_tracks_supplied_fields() -> None:
    model = OrganizationUpdate(external_id=TEST_EXTERNAL_ID, name=TEST_ORG_NAME, scopes="read")
    assert model.model_dump(exclude_unset=True) == {
        "external_id": TEST_EXTERNAL_ID,
        "name": TEST_ORG_NAME,
        "scopes": "read",
    }


def test_response_model_from_entity_with_none_scopes() -> None:
    class _Entity:
        id = uuid4()
        external_id = TEST_EXTERNAL_ID
        name = TEST_ORG_NAME
        scopes = None
        created_at = now.now()
        deleted_at = None

    model = Organization.model_validate(_Entity())
    assert model.scopes is None


def test_response_model_allows_scopes_no_longer_configured() -> None:
    """Narrowing the configured allow-list must not make existing records unreadable."""

    class _Entity:
        id = uuid4()
        external_id = TEST_EXTERNAL_ID
        name = TEST_ORG_NAME
        scopes = "admin"
        created_at = now.now()
        deleted_at = None

    model = Organization.model_validate(_Entity())
    assert model.scopes == "admin"
