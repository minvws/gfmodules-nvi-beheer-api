from datetime import datetime as now
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.organization import Organization, OrganizationCreate, OrganizationUpdate
from tests.conftest import TEST_ORG_NAME, TEST_REGISTER_ID


def test_create_should_succeed() -> None:
    model = OrganizationCreate(register_id=TEST_REGISTER_ID, name=TEST_ORG_NAME)
    assert model.register_id == TEST_REGISTER_ID
    assert model.name == TEST_ORG_NAME
    assert model.scopes is None


def test_create_with_scopes_should_succeed() -> None:
    model = OrganizationCreate(register_id=TEST_REGISTER_ID, name=TEST_ORG_NAME, scopes="read write")
    assert model.scopes == "read write"


def test_create_missing_register_id_should_raise() -> None:
    with pytest.raises(ValidationError):
        OrganizationCreate(name=TEST_ORG_NAME)  # type: ignore[call-arg]


def test_create_missing_name_should_raise() -> None:
    with pytest.raises(ValidationError):
        OrganizationCreate(register_id=TEST_REGISTER_ID)  # type: ignore[call-arg]


def test_update_should_succeed() -> None:
    model = OrganizationUpdate(name="New Name")
    assert model.name == "New Name"
    assert model.scopes is None


def test_update_is_partial_all_fields_optional() -> None:
    model = OrganizationUpdate()
    assert model.name is None
    assert model.scopes is None


def test_update_only_tracks_supplied_fields() -> None:
    model = OrganizationUpdate(scopes="read")
    assert model.model_dump(exclude_unset=True) == {"scopes": "read"}


def test_response_model_from_entity_with_none_scopes() -> None:
    class _Entity:
        id = uuid4()
        register_id = TEST_REGISTER_ID
        name = TEST_ORG_NAME
        scopes = None
        created_at = now.now()
        deleted_at = None

    model = Organization.model_validate(_Entity())
    assert model.scopes is None
