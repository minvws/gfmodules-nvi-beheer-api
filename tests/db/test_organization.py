from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import InvalidRequestError

from app.db.models.organization import OrganizationEntity
from app.db.repository.organization import OrganizationRepository
from tests.conftest import TEST_REGISTER_ID


def test_add_one(
    organization_repository: OrganizationRepository,
    organization_entity: OrganizationEntity,
) -> None:
    with organization_repository.db_session:
        result = organization_repository.add_one(organization_entity)
        assert result == organization_entity


def test_get_one_found(
    organization_repository: OrganizationRepository,
    organization_entity: OrganizationEntity,
) -> None:
    with organization_repository.db_session:
        organization_repository.add_one(organization_entity)
        result = organization_repository.get_one(organization_entity.id)
        assert result is not None
        assert result.id == organization_entity.id


def test_get_one_not_found(organization_repository: OrganizationRepository) -> None:
    with organization_repository.db_session:
        assert organization_repository.get_one(uuid4()) is None


def test_exists_found(
    organization_repository: OrganizationRepository,
    organization_entity: OrganizationEntity,
) -> None:
    with organization_repository.db_session:
        organization_repository.add_one(organization_entity)
        assert organization_repository.exists(organization_entity.id) is True


def test_exists_not_found(organization_repository: OrganizationRepository) -> None:
    with organization_repository.db_session:
        assert organization_repository.exists(uuid4()) is False


def test_get_one_by_register_id(
    organization_repository: OrganizationRepository,
    organization_entity: OrganizationEntity,
) -> None:
    with organization_repository.db_session:
        organization_repository.add_one(organization_entity)
        result = organization_repository.get_one_by_register_id(TEST_REGISTER_ID)
        assert result is not None
        assert result.register_id == TEST_REGISTER_ID


def test_update_success(
    organization_repository: OrganizationRepository,
    organization_entity: OrganizationEntity,
) -> None:
    with organization_repository.db_session:
        organization_repository.add_one(organization_entity)
        result = organization_repository.update(id=organization_entity.id, name="Updated Name")
        assert result is not None
        assert result.name == "Updated Name"


def test_update_ignores_invalid_fields(
    organization_repository: OrganizationRepository,
    organization_entity: OrganizationEntity,
) -> None:
    with organization_repository.db_session:
        organization_repository.add_one(organization_entity)
        result = organization_repository.update(id=organization_entity.id, non_existing_field="value")
        assert result is None


def test_update_not_found(organization_repository: OrganizationRepository) -> None:
    with organization_repository.db_session:
        assert organization_repository.update(uuid4(), name="Ghost") is None


def test_get_many_returns_all(
    organization_repository: OrganizationRepository,
    organization_entity: OrganizationEntity,
) -> None:
    entity_2 = OrganizationEntity(register_id="test-register-002", name="Another Organization")
    with organization_repository.db_session:
        organization_repository.add_one(organization_entity)
        organization_repository.add_one(entity_2)
        assert len(organization_repository.get_many()) == 2


def test_get_many_filters_by_register_id(
    organization_repository: OrganizationRepository,
    organization_entity: OrganizationEntity,
) -> None:
    entity_2 = OrganizationEntity(register_id="test-register-002", name="Another Organization")
    with organization_repository.db_session:
        organization_repository.add_one(organization_entity)
        organization_repository.add_one(entity_2)
        results = organization_repository.get_many(register_id=TEST_REGISTER_ID)
        assert len(results) == 1
        assert results[0].id == organization_entity.id


def test_get_many_excludes_deleted(
    organization_repository: OrganizationRepository,
    organization_entity: OrganizationEntity,
) -> None:
    with organization_repository.db_session:
        organization_repository.add_one(organization_entity)
        organization_repository.update(id=organization_entity.id, deleted_at=datetime.now())
        assert organization_repository.get_many() == []


def test_get_many_include_deleted_returns_deleted(
    organization_repository: OrganizationRepository,
    organization_entity: OrganizationEntity,
) -> None:
    with organization_repository.db_session:
        organization_repository.add_one(organization_entity)
        organization_repository.update(id=organization_entity.id, deleted_at=datetime.now())
        results = organization_repository.get_many(include_deleted=True)
        assert len(results) == 1
        assert results[0].id == organization_entity.id


def test_accessing_clients_raises_lazy_load(
    organization_repository: OrganizationRepository,
    organization_entity: OrganizationEntity,
) -> None:
    with organization_repository.db_session:
        organization_repository.add_one(organization_entity)
        result = organization_repository.get_one(organization_entity.id)
        assert result is not None
        with pytest.raises(InvalidRequestError):
            _ = result.clients
