from uuid import uuid4

import pytest

from app.models.organization import OrganizationCreate
from app.models.source import SourceCreate, SourceQueryParams, SourceUpdate
from app.services.exceptions import ConflictError, EntityHasActiveMemebersError, RecordNotFoundError
from app.services.organization import OrganizationService
from app.services.source.organization_source import OrganizationSourceService
from tests.conftest import TEST_SOURCE_ID, TEST_SOURCE_NAME


def test_get_one_should_succeed(
    organization_source_service: OrganizationSourceService,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    assert org.sources is not None
    expected = org.sources[0]

    actual = organization_source_service.get_one(org.id, expected.id)

    assert expected == actual


def test_get_one_should_raise_on_id_missmatch(
    organization_source_service: OrganizationSourceService,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
) -> None:

    org = organization_service.create_one(org_create_dto_1)
    assert org.sources is not None
    expected = org.sources[0]
    source = organization_source_service.get_one(org.id, expected.id)

    with pytest.raises(RecordNotFoundError):
        _ = organization_source_service.get_one(org.id, uuid4())

    with pytest.raises(RecordNotFoundError):
        _ = organization_source_service.get_one(uuid4(), source.id)


def test_get_many_should_succeed(
    organization_source_service: OrganizationSourceService,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    assert org.sources is not None

    expected = org.sources

    actual = organization_source_service.get_many(org.id, SourceQueryParams())

    assert expected == actual


@pytest.mark.parametrize(
    "params",
    [
        SourceQueryParams(source_id=TEST_SOURCE_ID),
        SourceQueryParams(name=TEST_SOURCE_NAME),
        SourceQueryParams(source_id=TEST_SOURCE_ID, name=TEST_SOURCE_NAME),
    ],
)
def test_get_many_should_succeed_on_params(
    organization_source_service: OrganizationSourceService,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
    params: SourceQueryParams,
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    assert org.sources is not None

    expected = [org.sources[0]]
    actual = organization_source_service.get_many(org.id, params)

    assert expected == actual


def test_get_many_shoul_return_empty_list_one_no_match(
    organization_source_service: OrganizationSourceService,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
) -> None:
    org = organization_service.create_one(org_create_dto_1)

    actual = organization_source_service.get_many(org.id, SourceQueryParams(source_id="some unknown id"))

    assert actual == []


def test_get_many_should_raise_one_wrong_org_id(
    organization_source_service: OrganizationSourceService,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
) -> None:
    _ = organization_service.create_one(org_create_dto_1)

    with pytest.raises(RecordNotFoundError):
        _ = organization_source_service.get_many(uuid4(), SourceQueryParams())


def test_create_one_should_succeed(
    organization_source_service: OrganizationSourceService,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
    source_create_dto_1: SourceCreate,
) -> None:
    org_create_dto_1.sources = None
    org_create_dto_1.clients = None
    org = organization_service.create_one(org_create_dto_1)

    expected = organization_source_service.create_one(org.id, source_create_dto_1)
    actual = organization_source_service.get_one(org.id, expected.id)

    assert expected == actual


def test_create_one_should_raise_on_unknown_org(
    organization_source_service: OrganizationSourceService,
    source_create_dto_1: SourceCreate,
) -> None:
    with pytest.raises(RecordNotFoundError):
        _ = organization_source_service.create_one(uuid4(), source_create_dto_1)


def test_create_one_should_raise_on_conflict(
    organization_source_service: OrganizationSourceService,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
    source_create_dto_1: SourceCreate,
) -> None:

    org_create_dto_1.sources = None
    org_create_dto_1.clients = None
    org = organization_service.create_one(org_create_dto_1)

    _ = organization_source_service.create_one(org.id, source_create_dto_1)

    with pytest.raises(ConflictError):
        _ = organization_source_service.create_one(org.id, source_create_dto_1)


def test_update_one_should_succeed(
    organization_source_service: OrganizationSourceService,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    assert org.sources is not None
    target = org.sources[0]
    dto = SourceUpdate(id=target.id, source_id="update-source", name="updated-name")

    expected = organization_source_service.update_one(org.id, target.id, dto)
    actual = organization_source_service.get_one(org.id, target.id)

    assert target.id == expected.id
    assert target.id == actual.id
    assert expected == actual


def test_update_one_should_raise_on_id_mismatch(
    organization_source_service: OrganizationSourceService,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    assert org.sources is not None
    target = org.sources[0]
    dto = SourceUpdate(id=target.id, source_id="update-source", name="updated-name")

    with pytest.raises(RecordNotFoundError):
        _ = organization_source_service.update_one(org.id, uuid4(), dto)

    with pytest.raises(RecordNotFoundError):
        _ = organization_source_service.update_one(uuid4(), target.id, dto)


def test_delete_one_should_succeed(
    organization_source_service: OrganizationSourceService,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
) -> None:
    org_create_dto_1.clients = None
    org = organization_service.create_one(org_create_dto_1)
    assert org.sources is not None
    target = org.sources[0]

    _ = organization_source_service.delete_one(org.id, target.id)

    with pytest.raises(RecordNotFoundError):
        _ = organization_source_service.get_one(org.id, target.id)


def test_delete_one_should_raise_on_active_memebers(
    organization_source_service: OrganizationSourceService,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    assert org.sources is not None
    assert org.clients is not None
    target = org.sources[0]
    client = org.clients[0]

    with pytest.raises(EntityHasActiveMemebersError):
        _ = organization_source_service.delete_one(org.id, target.id)

    assert client.sources is not None
    assert target.id in [s.id for s in client.sources]


def test_delete_one_should_raise_on_id_missmatch(
    organization_source_service: OrganizationSourceService,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
) -> None:

    org = organization_service.create_one(org_create_dto_1)
    assert org.sources is not None
    target = org.sources[0]

    with pytest.raises(RecordNotFoundError):
        _ = organization_source_service.delete_one(uuid4(), target.id)

    with pytest.raises(RecordNotFoundError):
        _ = organization_source_service.delete_one(org.id, uuid4())
