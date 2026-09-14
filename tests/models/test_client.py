from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.certificates import CertificateCreate
from app.models.client import (
    ClientCreate,
    ClientQueryParams,
    ClientResolveRequest,
    ClientUpdate,
)
from app.models.source import SourceCreate
from app.models.ura import UraNumber
from tests.conftest import TEST_CLIENT_NAME, TEST_OIN


def test_create_should_succeed(cert_create_dto_1: CertificateCreate, source_create_dto_1: SourceCreate) -> None:
    model = ClientCreate(name=TEST_CLIENT_NAME, certificates=[cert_create_dto_1], sources=[source_create_dto_1])
    assert model.name == TEST_CLIENT_NAME
    assert model.sources is not None
    assert model.certificates is not None
    assert model.certificates == [cert_create_dto_1]
    assert model.sources == [source_create_dto_1]


def test_create_with_scopes_should_succeed() -> None:
    model = ClientCreate(name="Test Client", scopes="nvi:read")
    assert model.scopes == "nvi:read"
    assert model.sanatized_scopes == ["nvi:read"]


def test_create_missing_name_should_raise() -> None:
    with pytest.raises(ValidationError):
        ClientCreate(description="some desc")  # type: ignore[call-arg]


def test_update_is_partial_all_fields_optional() -> None:
    model = ClientUpdate(id=uuid4(), name="some name")
    assert model.description is None
    assert model.sources is None
    assert model.certificates is None


def test_update_only_tracks_supplied_fields() -> None:
    mock_id = uuid4()
    model = ClientUpdate(id=mock_id, name="New Name")
    assert model.model_dump(exclude_unset=True) == {"id": mock_id, "name": "New Name"}


def test_query_params_all_optional_and_track_supplied_only() -> None:
    assert ClientQueryParams().model_dump(exclude_unset=True) == {}
    params = ClientQueryParams(name="some name", scopes="nvi:read")
    assert params.model_dump(exclude_unset=True) == {"name": "some name", "scopes": "nvi:read"}


def test_resolve_request_should_succeed() -> None:
    org_ura = UraNumber("12345678")
    model = ClientResolveRequest(
        client_organization_id=TEST_OIN,
        client_common_name="Test Client",
        organization_id=org_ura,
    )
    assert str(model.client_organization_id) == str(TEST_OIN)
    assert str(model.organization_id) == str(org_ura)


def test_resolve_request_missing_org_id_should_raise() -> None:
    with pytest.raises(ValidationError):
        ClientResolveRequest(  # type: ignore[call-arg]
            client_organization_id=TEST_OIN,
            client_common_name="Test Client",
        )
