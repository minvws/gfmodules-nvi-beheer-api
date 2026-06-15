from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import InvalidRequestError

from app.db.models.client import ClientEntity
from app.db.repository.client import ClientRepository
from tests.conftest import TEST_OIN


def test_add_one(
    client_repository: ClientRepository,
    client_entity: ClientEntity,
) -> None:
    with client_repository.db_session:
        result = client_repository.add_one(client_entity)
        assert result == client_entity


def test_get_one_found(
    client_repository: ClientRepository,
    client_entity: ClientEntity,
) -> None:
    with client_repository.db_session:
        client_repository.add_one(client_entity)
        result = client_repository.get_one(client_entity.organization_id, client_entity.id)
        assert result is not None
        assert result.id == client_entity.id


def test_get_one_not_found(
    client_repository: ClientRepository,
    client_entity: ClientEntity,
) -> None:
    with client_repository.db_session:
        assert client_repository.get_one(uuid4(), client_entity.id) is None


def test_get_one_wrong_organization(
    client_repository: ClientRepository,
    client_entity: ClientEntity,
) -> None:
    with client_repository.db_session:
        client_repository.add_one(client_entity)
        assert client_repository.get_one(uuid4(), client_entity.id) is None


def test_exists_found(
    client_repository: ClientRepository,
    client_entity: ClientEntity,
) -> None:
    with client_repository.db_session:
        client_repository.add_one(client_entity)
        assert client_repository.exists(client_entity.organization_id, client_entity.id) is True


def test_exists_not_found(
    client_repository: ClientRepository,
    client_entity: ClientEntity,
) -> None:
    with client_repository.db_session:
        client_repository.add_one(client_entity)
        assert client_repository.exists(uuid4(), client_entity.id) is False


def test_update_success(
    client_repository: ClientRepository,
    client_entity: ClientEntity,
) -> None:
    with client_repository.db_session:
        client_repository.add_one(client_entity)
        result = client_repository.update(client_entity.organization_id, client_entity.id, common_name="Updated Name")
        assert result is not None
        assert result.common_name == "Updated Name"


def test_update_not_found(client_repository: ClientRepository) -> None:
    with client_repository.db_session:
        assert client_repository.update(uuid4(), uuid4(), common_name="Not Found") is None


def test_get_many_returns_all(
    client_repository: ClientRepository,
    client_entity: ClientEntity,
) -> None:
    entity_2 = ClientEntity(
        organization_id=client_entity.organization_id,
        mandate_id="mandate-002",
        oin=TEST_OIN,
        common_name="Another Client",
    )
    with client_repository.db_session:
        client_repository.add_one(client_entity)
        client_repository.add_one(entity_2)
        assert len(client_repository.get_many(organization_id=client_entity.organization_id)) == 2


def test_get_many_filters_by_oin(
    client_repository: ClientRepository,
    client_entity: ClientEntity,
) -> None:
    entity_2 = ClientEntity(
        organization_id=client_entity.organization_id,
        mandate_id="mandate-002",
        oin="00000099000000002000",
        common_name="Another Client",
    )
    with client_repository.db_session:
        client_repository.add_one(client_entity)
        client_repository.add_one(entity_2)
        results = client_repository.get_many(organization_id=client_entity.organization_id, oin=TEST_OIN)
        assert len(results) == 1
        assert results[0].id == client_entity.id


def test_get_many_excludes_deleted(
    client_repository: ClientRepository,
    client_entity: ClientEntity,
) -> None:
    with client_repository.db_session:
        client_repository.add_one(client_entity)
        client_repository.update(client_entity.organization_id, client_entity.id, deleted_at=datetime.now())
        assert client_repository.get_many(organization_id=client_entity.organization_id) == []


def test_get_many_include_deleted_returns_deleted(
    client_repository: ClientRepository,
    client_entity: ClientEntity,
) -> None:
    with client_repository.db_session:
        client_repository.add_one(client_entity)
        client_repository.update(client_entity.organization_id, client_entity.id, deleted_at=datetime.now())
        results = client_repository.get_many(organization_id=client_entity.organization_id, include_deleted=True)
        assert len(results) == 1
        assert results[0].id == client_entity.id


def test_get_many_scoped_to_organization(
    client_repository: ClientRepository,
    client_entity: ClientEntity,
) -> None:
    with client_repository.db_session:
        client_repository.add_one(client_entity)
        assert client_repository.get_many(organization_id=uuid4()) == []


def test_accessing_organization_raises_lazy_load(
    client_repository: ClientRepository,
    client_entity: ClientEntity,
) -> None:
    with client_repository.db_session:
        client_repository.add_one(client_entity)
        result = client_repository.get_one(client_entity.organization_id, client_entity.id)
        assert result is not None
        with pytest.raises(InvalidRequestError):
            _ = result.organization
