from uuid import UUID, uuid4

from app.db.models.organization import OrganizationEntity
from app.services.organization import OrganizationService
from tests.conftest import TEST_ORG_NAME, TEST_REGISTER_ID

SECOND_ORG_REG_ID = "test-register-002"
SECOND_ORG_NAME = "Second Test Organization"


def test_create_one_should_succeed(
    organization_service: OrganizationService,
    organization_entity: OrganizationEntity,
) -> None:
    result = organization_service.create_one(
        register_id=organization_entity.register_id,
        name=organization_entity.name,
    )
    assert isinstance(result.id, UUID)
    assert result.register_id == organization_entity.register_id
    assert result.name == organization_entity.name


def test_create_one_with_scopes(
    organization_service: OrganizationService,
) -> None:
    result = organization_service.create_one(
        register_id=TEST_REGISTER_ID,
        name=TEST_ORG_NAME,
        scopes="read write",
    )
    assert result.scopes == "read write"


def test_get_one_should_succeed(
    organization_service: OrganizationService,
    organization_entity: OrganizationEntity,
) -> None:
    created = organization_service.create_one(
        register_id=organization_entity.register_id,
        name=organization_entity.name,
    )
    result = organization_service.get_one(created.id)
    assert result is not None
    assert result.id == created.id
    assert result.register_id == created.register_id


def test_get_one_returns_none_when_not_found(
    organization_service: OrganizationService,
) -> None:
    result = organization_service.get_one(uuid4())
    assert result is None


def test_delete_one_soft_deletes(
    organization_service: OrganizationService,
    organization_entity: OrganizationEntity,
) -> None:
    created = organization_service.create_one(
        register_id=organization_entity.register_id,
        name=organization_entity.name,
    )
    organization_service.delete_one(created.id)
    result = organization_service.get_one(created.id)
    assert result is None


def test_delete_one_returns_none_when_not_found(
    organization_service: OrganizationService,
) -> None:
    result = organization_service.delete_one(uuid4())
    assert result is None


def test_update_one_should_succeed(
    organization_service: OrganizationService,
    organization_entity: OrganizationEntity,
) -> None:
    created = organization_service.create_one(
        register_id=organization_entity.register_id,
        name=organization_entity.name,
    )
    result = organization_service.update_one(created.id, name="New Name")
    assert result is not None
    assert result.name == "New Name"
    assert result.id == created.id


def test_update_one_scopes(
    organization_service: OrganizationService,
    organization_entity: OrganizationEntity,
) -> None:
    created = organization_service.create_one(
        register_id=organization_entity.register_id,
        name=organization_entity.name,
    )
    result = organization_service.update_one(created.id, scopes="read write")
    assert result is not None
    assert result.scopes == "read write"


def test_update_one_returns_none_when_not_found(
    organization_service: OrganizationService,
) -> None:
    result = organization_service.update_one(uuid4(), name="not-found")
    assert result is None


def test_get_many_returns_empty_when_none(
    organization_service: OrganizationService,
) -> None:
    results = organization_service.get_many()
    assert results == []


def test_get_many_returns_all(
    organization_service: OrganizationService,
    organization_entity: OrganizationEntity,
) -> None:
    organization_service.create_one(
        register_id=organization_entity.register_id,
        name=organization_entity.name,
    )
    organization_service.create_one(register_id=SECOND_ORG_REG_ID, name=SECOND_ORG_NAME)
    results = organization_service.get_many()
    assert len(results) == 2


def test_get_many_excludes_deleted(
    organization_service: OrganizationService,
    organization_entity: OrganizationEntity,
) -> None:
    created = organization_service.create_one(
        register_id=organization_entity.register_id,
        name=organization_entity.name,
    )
    organization_service.delete_one(created.id)
    results = organization_service.get_many()
    assert results == []


def test_get_many_include_deleted_returns_deleted(
    organization_service: OrganizationService,
    organization_entity: OrganizationEntity,
) -> None:
    created = organization_service.create_one(
        register_id=organization_entity.register_id,
        name=organization_entity.name,
    )
    organization_service.delete_one(created.id)
    results = organization_service.get_many(include_deleted=True)
    assert len(results) == 1
    assert results[0].id == created.id


def test_get_many_filters_by_register_id(
    organization_service: OrganizationService,
    organization_entity: OrganizationEntity,
) -> None:
    organization_service.create_one(
        register_id=organization_entity.register_id,
        name=organization_entity.name,
    )
    organization_service.create_one(register_id=SECOND_ORG_REG_ID, name=SECOND_ORG_NAME)

    results = organization_service.get_many(register_id=organization_entity.register_id)
    assert len(results) == 1
    assert results[0].register_id == organization_entity.register_id


def test_get_many_filters_by_name(
    organization_service: OrganizationService,
) -> None:
    organization_service.create_one(register_id=TEST_REGISTER_ID, name=TEST_ORG_NAME)
    organization_service.create_one(register_id=SECOND_ORG_REG_ID, name=SECOND_ORG_NAME)
    results = organization_service.get_many(name=TEST_ORG_NAME)
    assert len(results) == 1
    assert results[0].name == TEST_ORG_NAME


def test_get_many_filters_by_scopes_contains(
    organization_service: OrganizationService,
) -> None:
    organization_service.create_one(register_id=TEST_REGISTER_ID, name=TEST_ORG_NAME, scopes="read")
    organization_service.create_one(register_id=SECOND_ORG_REG_ID, name=SECOND_ORG_NAME, scopes="read write")
    # "read" is contained in both organizations' scope sets.
    assert len(organization_service.get_many(scopes="read")) == 2
    # "write" only belongs to ORG-2.
    write_only = organization_service.get_many(scopes="write")
    assert len(write_only) == 1
    assert write_only[0].name == SECOND_ORG_NAME
    # Requesting multiple scopes requires all of them to be present.
    both = organization_service.get_many(scopes="read write")
    assert len(both) == 1
    assert both[0].name == SECOND_ORG_NAME
