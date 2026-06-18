import pytest
from pydantic import ValidationError

from app.models.client import (
    ClientCreate,
    ClientQueryParams,
    ClientResolveRequest,
    ClientUpdate,
)
from app.models.ura import UraNumber
from tests.conftest import TEST_OIN


def test_create_should_succeed() -> None:
    model = ClientCreate(oin=TEST_OIN, common_name="Test Client")
    assert str(model.oin) == str(TEST_OIN)
    assert model.common_name == "Test Client"
    assert model.source_id is None
    assert model.scopes is None


def test_create_source_id_is_optional() -> None:
    model = ClientCreate(oin=TEST_OIN, common_name="Test Client", source_id="source-1")
    assert model.source_id == "source-1"


def test_create_with_scopes_should_succeed() -> None:
    model = ClientCreate(oin=TEST_OIN, common_name="Test Client", scopes="read")
    assert model.scopes == "read"


def test_create_missing_oin_should_raise() -> None:
    with pytest.raises(ValidationError):
        ClientCreate(common_name="Test Client")  # type: ignore[call-arg]


def test_create_missing_common_name_should_raise() -> None:
    with pytest.raises(ValidationError):
        ClientCreate(oin=TEST_OIN)  # type: ignore[call-arg]


def test_update_is_partial_all_fields_optional() -> None:
    model = ClientUpdate()
    assert model.oin is None
    assert model.common_name is None
    assert model.source_id is None
    assert model.scopes is None


def test_update_only_tracks_supplied_fields() -> None:
    model = ClientUpdate(common_name="New Name")
    assert model.model_dump(exclude_unset=True) == {"common_name": "New Name"}


def test_update_can_set_oin_and_source_id() -> None:
    model = ClientUpdate(oin=TEST_OIN, source_id="source-1")
    assert str(model.oin) == str(TEST_OIN)
    assert model.source_id == "source-1"


def test_query_params_all_optional_and_track_supplied_only() -> None:
    assert ClientQueryParams().model_dump(exclude_unset=True) == {}
    params = ClientQueryParams(common_name="CN-1", scopes="read")
    assert params.model_dump(exclude_unset=True) == {"common_name": "CN-1", "scopes": "read"}


def test_resolve_request_should_succeed() -> None:
    org_ura = UraNumber("12345678")
    model = ClientResolveRequest(
        oin=TEST_OIN,
        common_name="Test Client",
        org_ura=org_ura,
    )
    assert str(model.oin) == str(TEST_OIN)
    assert str(model.org_ura) == str(org_ura)


def test_resolve_request_missing_org_ura_should_raise() -> None:
    with pytest.raises(ValidationError):
        ClientResolveRequest(  # type: ignore[call-arg]
            oin=TEST_OIN,
            common_name="Test Client",
        )
