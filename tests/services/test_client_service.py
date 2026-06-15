from typing import Any
from uuid import UUID, uuid4

import pytest

from app.db.models.client import ClientEntity
from app.db.models.organization import OrganizationEntity
from app.models.oin import Oin
from app.services.client import ClientService
from app.services.exceptions import ScopesNotGrantedError
from app.services.organization import OrganizationService
from tests.conftest import TEST_OIN

ALT_OIN = "00000099000000002000"


def _create_client(
    service: ClientService,
    organization_id: UUID,
    *,
    oin: str = TEST_OIN,
    common_name: str = "CN-1",
    mandate_id: str = "mandate-1",
    scopes: str | None = None,
) -> ClientEntity:
    return service.create_one(
        organization_id=organization_id,
        oin=Oin(oin),
        common_name=common_name,
        mandate_id=mandate_id,
        scopes=scopes,
    )


def _scoped_org(organization_service: OrganizationService, scopes: str) -> OrganizationEntity:
    return organization_service.create_one(register_id="00000099000000009000", name="Scoped Org", scopes=scopes)


def test_create_one_should_succeed(
    client_service: ClientService,
    persisted_organization: OrganizationEntity,
) -> None:
    result = _create_client(client_service, persisted_organization.id)
    assert isinstance(result.id, UUID)
    assert result.organization_id == persisted_organization.id
    assert result.oin == TEST_OIN
    assert result.common_name == "CN-1"
    assert result.mandate_id == "mandate-1"


@pytest.mark.parametrize(
    "real_client, real_org, expected_found",
    [
        (True, True, True),
        (False, True, False),
        (True, False, False),
    ],
)
def test_get_one_lookup(
    client_service: ClientService,
    persisted_organization: OrganizationEntity,
    real_client: bool,
    real_org: bool,
    expected_found: bool,
) -> None:
    created = _create_client(client_service, persisted_organization.id)
    client_id = created.id if real_client else uuid4()
    organization_id = persisted_organization.id if real_org else uuid4()
    assert (client_service.get_one(client_id, organization_id) is not None) == expected_found


@pytest.mark.parametrize("exists", [True, False])
def test_delete_one(
    client_service: ClientService,
    persisted_organization: OrganizationEntity,
    exists: bool,
) -> None:
    created = _create_client(client_service, persisted_organization.id)
    target = created.id if exists else uuid4()
    result = client_service.delete_one(target, persisted_organization.id)
    assert (result is not None) == exists
    assert (client_service.get_one(created.id, persisted_organization.id) is None) == exists


@pytest.mark.parametrize("exists", [True, False])
def test_update_one(
    client_service: ClientService,
    persisted_organization: OrganizationEntity,
    exists: bool,
) -> None:
    created = _create_client(client_service, persisted_organization.id)
    target = created.id if exists else uuid4()
    result = client_service.update_one(target, persisted_organization.id, common_name="Updated Client")
    if exists:
        assert result is not None
        assert result.id == created.id
        assert result.common_name == "Updated Client"
    else:
        assert result is None


def test_update_one_can_change_oin_and_mandate_id(
    client_service: ClientService,
    persisted_organization: OrganizationEntity,
) -> None:
    created = _create_client(client_service, persisted_organization.id, mandate_id="mandate-old")
    result = client_service.update_one(
        created.id, persisted_organization.id, oin=Oin(ALT_OIN), mandate_id="mandate-new"
    )
    assert result is not None
    assert result.oin == ALT_OIN
    assert isinstance(result.oin, str)
    assert result.mandate_id == "mandate-new"
    assert client_service.get_one(created.id, persisted_organization.id) is not None


@pytest.mark.parametrize("count", [0, 1, 2])
def test_get_many_returns_active_clients(
    client_service: ClientService,
    persisted_organization: OrganizationEntity,
    count: int,
) -> None:
    for i in range(count):
        _create_client(client_service, persisted_organization.id, mandate_id=f"mandate-{i}")
    assert len(client_service.get_many(organization_id=persisted_organization.id)) == count


def test_get_many_scoped_to_organization(
    client_service: ClientService,
    persisted_organization: OrganizationEntity,
) -> None:
    _create_client(client_service, persisted_organization.id)
    assert client_service.get_many(organization_id=uuid4()) == []


@pytest.mark.parametrize("include_deleted, expected_count", [(False, 0), (True, 1)])
def test_get_many_deleted_visibility(
    client_service: ClientService,
    persisted_organization: OrganizationEntity,
    include_deleted: bool,
    expected_count: int,
) -> None:
    created = _create_client(client_service, persisted_organization.id)
    client_service.delete_one(created.id, persisted_organization.id)
    results = client_service.get_many(organization_id=persisted_organization.id, include_deleted=include_deleted)
    assert len(results) == expected_count


@pytest.mark.parametrize(
    "filter_kwargs, attr, expected",
    [
        ({"oin": Oin(TEST_OIN)}, "oin", TEST_OIN),
        ({"common_name": "CN-1"}, "common_name", "CN-1"),
        ({"mandate_id": "mandate-a"}, "mandate_id", "mandate-a"),
    ],
)
def test_get_many_single_filter(
    client_service: ClientService,
    persisted_organization: OrganizationEntity,
    filter_kwargs: dict[str, Any],
    attr: str,
    expected: str,
) -> None:
    _create_client(client_service, persisted_organization.id, oin=TEST_OIN, common_name="CN-1", mandate_id="mandate-a")
    _create_client(client_service, persisted_organization.id, oin=ALT_OIN, common_name="CN-2", mandate_id="mandate-b")
    results = client_service.get_many(organization_id=persisted_organization.id, **filter_kwargs)
    assert len(results) == 1
    assert getattr(results[0], attr) == expected


@pytest.mark.parametrize(
    "query, expected_common_names",
    [
        ("read", {"CN-1", "CN-2"}),
        ("write", {"CN-2"}),
        ("read write", {"CN-2"}),
        ("rea", set()),
    ],
)
def test_get_many_filters_by_scopes(
    client_service: ClientService,
    organization_service: OrganizationService,
    query: str,
    expected_common_names: set[str],
) -> None:
    org = _scoped_org(organization_service, "read write")
    _create_client(client_service, org.id, oin=TEST_OIN, common_name="CN-1", mandate_id="mandate-a", scopes="read")
    _create_client(client_service, org.id, oin=ALT_OIN, common_name="CN-2", mandate_id="mandate-b", scopes="read write")
    results = client_service.get_many(organization_id=org.id, scopes=query)
    assert {client.common_name for client in results} == expected_common_names


@pytest.mark.parametrize(
    "org_scopes, requested, expected_scopes, raises",
    [
        ("read write delete", "read write", "read write", False),
        ("read", None, None, False),
        ("read", "read write", None, True),
    ],
)
def test_create_one_scope_enforcement(
    client_service: ClientService,
    organization_service: OrganizationService,
    org_scopes: str,
    requested: str | None,
    expected_scopes: str | None,
    raises: bool,
) -> None:
    org = _scoped_org(organization_service, org_scopes)
    if raises:
        with pytest.raises(ScopesNotGrantedError):
            _create_client(client_service, org.id, scopes=requested)
    else:
        result = _create_client(client_service, org.id, scopes=requested)
        assert result.scopes == expected_scopes


@pytest.mark.parametrize(
    "org_scopes, requested, raises",
    [
        ("read write", "read", False),
        ("read", "read write", True),
    ],
)
def test_update_one_scope_enforcement(
    client_service: ClientService,
    organization_service: OrganizationService,
    org_scopes: str,
    requested: str,
    raises: bool,
) -> None:
    org = _scoped_org(organization_service, org_scopes)
    created = _create_client(client_service, org.id)
    if raises:
        with pytest.raises(ScopesNotGrantedError):
            client_service.update_one(created.id, org.id, scopes=requested)
    else:
        result = client_service.update_one(created.id, org.id, scopes=requested)
        assert result is not None
        assert result.scopes == requested


@pytest.mark.parametrize(
    "common_name, mandate_id, expected",
    [
        ("Scoped Client", "mandate-xyz", "read write"),
        ("Nobody", "mandate-none", None),
    ],
)
def test_resolve(
    client_service: ClientService,
    organization_service: OrganizationService,
    common_name: str,
    mandate_id: str,
    expected: str | None,
) -> None:
    org = _scoped_org(organization_service, "read write delete")
    _create_client(client_service, org.id, common_name="Scoped Client", mandate_id="mandate-xyz", scopes="read write")
    resolved = client_service.resolve(oin=Oin(TEST_OIN), common_name=common_name, mandate_id=mandate_id)
    assert resolved == expected
