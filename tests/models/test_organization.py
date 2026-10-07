from collections.abc import Generator
from datetime import UTC
from datetime import datetime as now
from typing import Any
from uuid import uuid4

import inject
import pytest
from pydantic import ValidationError

from app.models.organization import Organization, OrganizationCreate, OrganizationUpdate
from app.models.scopes import AuthorizationScope
from app.models.source import SourceCreate
from tests.conftest import TEST_EXTERNAL_ID, TEST_ORG_NAME, TEST_SOURCE_ID


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
    assert model.sources is None


@pytest.mark.parametrize(
    "sources",
    [
        None,
        [],
        [SourceCreate(source_id="source-1", name="Source 1")],
        [
            SourceCreate(source_id="source-1", name="Source 1"),
            SourceCreate(source_id="source-2", name="Source 2"),
        ],
    ],
)
def test_create_with_unique_sources_should_succeed(sources: list[SourceCreate] | None) -> None:
    model = OrganizationCreate(external_id=TEST_EXTERNAL_ID, name=TEST_ORG_NAME, sources=sources)

    assert model.sources == sources


@pytest.mark.parametrize(
    "source_ids, duplicate_ids",
    [
        ([TEST_SOURCE_ID, TEST_SOURCE_ID], TEST_SOURCE_ID),
        (["source-2", "source-1", "source-2", "unique", "source-1", "source-2"], "source-2 source-1"),
    ],
)
def test_create_with_duplicate_source_ids_should_raise(source_ids: list[str], duplicate_ids: str) -> None:
    sources = [SourceCreate(source_id=source_id, name=f"Source {index}") for index, source_id in enumerate(source_ids)]

    with pytest.raises(ValidationError) as exc:
        OrganizationCreate(external_id=TEST_EXTERNAL_ID, name=TEST_ORG_NAME, sources=sources)

    errors = exc.value.errors()
    assert len(errors) == 1
    assert errors[0]["loc"] == ("sources",)
    assert errors[0]["type"] == "value_error"
    assert errors[0]["msg"] == f"Value error, Duplicate source_id values: {duplicate_ids}"


def test_create_with_scopes_should_succeed() -> None:
    model = OrganizationCreate(
        external_id=TEST_EXTERNAL_ID,
        name=TEST_ORG_NAME,
        scopes=[AuthorizationScope("nvi:read"), AuthorizationScope("nvi:create")],
    )
    assert model.scopes == [AuthorizationScope("nvi:read"), AuthorizationScope("nvi:create")]


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


def test_update_only_tracks_supplied_fields() -> None:
    model = OrganizationUpdate(external_id=TEST_EXTERNAL_ID, name=TEST_ORG_NAME)
    assert model.model_dump(exclude_unset=True) == {
        "external_id": TEST_EXTERNAL_ID,
        "name": TEST_ORG_NAME,
    }


def test_response_model_from_entity_with_none_scopes() -> None:
    class _Entity:
        id = uuid4()
        external_id = TEST_EXTERNAL_ID
        name = TEST_ORG_NAME
        scopes = None
        created_at = now.now(UTC)
        deleted_at = None

    model = Organization.model_validate(_Entity())
    assert model.scopes is None
