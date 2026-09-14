from uuid import uuid4

import pytest

from app.models.organization import OrganizationCreate
from app.models.source import SourceQueryParams
from app.services.exceptions import ConflictError, RecordNotFoundError
from app.services.organization import OrganizationService
from app.services.source.client_source import ClientSourceService
from tests.conftest import TEST_SOURCE_ID, TEST_SOURCE_NAME


def test_get_one_should_succeed(
    client_source_service: ClientSourceService,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    assert org.clients is not None
    client = org.clients[0]
    assert client.sources is not None
    expected = client.sources[0]

    actual = client_source_service.get_one(org.id, client.id, expected.id)

    assert expected == actual


def test_get_one_should_raise_on_id_missmatch(
    client_source_service: ClientSourceService,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    assert org.clients is not None
    client = org.clients[0]
    assert client.sources is not None
    source = client.sources[0]

    with pytest.raises(RecordNotFoundError):
        _ = client_source_service.get_one(uuid4(), client.id, source.id)

    with pytest.raises(RecordNotFoundError):
        _ = client_source_service.get_one(org.id, uuid4(), source.id)

    with pytest.raises(RecordNotFoundError):
        _ = client_source_service.get_one(org.id, client.id, uuid4())


def test_get_many_should_succeed(
    client_source_service: ClientSourceService,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    assert org.clients is not None
    client = org.clients[0]
    assert client.sources is not None
    expected = client.sources

    actual = client_source_service.get_many(org.id, client.id, SourceQueryParams())

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
    client_source_service: ClientSourceService,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
    params: SourceQueryParams,
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    assert org.clients is not None
    client = org.clients[0]
    assert client.sources is not None
    expected = [client.sources[0]]

    actual = client_source_service.get_many(org.id, client.id, params)

    assert expected == actual


def test_get_many_should_return_empty_list_on_unknown_params(
    client_source_service: ClientSourceService,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    assert org.clients is not None
    client = org.clients[0]
    assert client.sources is not None

    actual = client_source_service.get_many(org.id, client.id, SourceQueryParams(source_id="some-uknown-id"))

    assert actual == []


def test_get_many_should_raise_on_id_missmatch(
    client_source_service: ClientSourceService,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    assert org.clients is not None
    client = org.clients[0]
    assert client.sources is not None

    with pytest.raises(RecordNotFoundError):
        _ = client_source_service.get_many(org.id, uuid4(), SourceQueryParams())

    with pytest.raises(RecordNotFoundError):
        _ = client_source_service.get_many(uuid4(), client.id, SourceQueryParams())


def test_assigne_one_should_succeed(
    client_source_service: ClientSourceService,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
) -> None:
    assert org_create_dto_1.clients is not None
    org_create_dto_1.clients[0].sources = None
    org = organization_service.create_one(org_create_dto_1)
    assert org.clients is not None
    assert org.sources is not None
    client = org.clients[0]
    target = org.sources[0]

    actual = client_source_service.assign_one(org.id, client.id, target.id)

    assert actual == target


def test_assigne_one_should_raise_on_conflict(
    client_source_service: ClientSourceService,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    assert org.sources is not None
    target = org.sources[0]
    assert org.clients is not None
    client = org.clients[0]
    assert client.sources is not None

    assert target.id in [s.id for s in client.sources]
    with pytest.raises(ConflictError):
        _ = client_source_service.assign_one(org.id, client.id, target.id)


def test_assigne_one_should_raise_on_missmatch(
    client_source_service: ClientSourceService,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    assert org.clients is not None
    assert org.sources is not None
    client = org.clients[0]
    target = org.sources[0]

    with pytest.raises(RecordNotFoundError):
        _ = client_source_service.assign_one(org.id, client.id, uuid4())

    with pytest.raises(RecordNotFoundError):
        _ = client_source_service.assign_one(org.id, uuid4(), target.id)

    with pytest.raises(RecordNotFoundError):
        _ = client_source_service.assign_one(uuid4(), client.id, target.id)


def test_unassigne_one_should_succeed(
    client_source_service: ClientSourceService,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    assert org.clients is not None
    assert org.sources is not None
    client = org.clients[0]
    target = org.sources[0]

    _ = client_source_service.unassign_one(org.id, client.id, target.id)

    assert client.sources is not None
    assert target.id in [s.id for s in client.sources]
    with pytest.raises(RecordNotFoundError):
        _ = client_source_service.get_one(org.id, client.id, target.id)


def test_unassigne_one_should_raise_on_id_missmatch(
    client_source_service: ClientSourceService,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    assert org.clients is not None
    assert org.sources is not None
    client = org.clients[0]
    target = org.sources[0]

    with pytest.raises(RecordNotFoundError):
        _ = client_source_service.unassign_one(org.id, client.id, uuid4())

    with pytest.raises(RecordNotFoundError):
        _ = client_source_service.unassign_one(org.id, uuid4(), target.id)

    with pytest.raises(RecordNotFoundError):
        _ = client_source_service.unassign_one(uuid4(), client.id, target.id)
