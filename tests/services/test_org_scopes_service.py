from uuid import uuid4

import pytest

from app.models.organization import OrganizationCreate
from app.models.scopes import AuthorizationScope
from app.services.exceptions import ConflictError, RecordNotFoundError
from app.services.organization import OrganizationService
from app.services.scopes.org_scopes import OrganizationScopesService


def test_assigne_one_should_succeed(
    org_create_dto_1: OrganizationCreate,
    organization_service: OrganizationService,
    org_scopes_service: OrganizationScopesService,
) -> None:
    org_create_dto_1.scopes = None
    org_create_dto_1.clients = None

    org = organization_service.create_one(org_create_dto_1)
    updated_org = org_scopes_service.assigne_one(org.id, AuthorizationScope.CREATE)

    assert updated_org.scopes is not None
    assert len(updated_org.scopes) == 1
    assert updated_org.scopes[0].name == AuthorizationScope.CREATE.name


def test_assigne_one_should_raise_when_org_not_found(
    org_scopes_service: OrganizationScopesService,
) -> None:
    with pytest.raises(RecordNotFoundError):
        _ = org_scopes_service.assigne_one(uuid4(), AuthorizationScope.CREATE)


def test_assigne_one_should_raise_when_org_does_not_have_scope(
    org_create_dto_1: OrganizationCreate,
    organization_service: OrganizationService,
    org_scopes_service: OrganizationScopesService,
) -> None:
    org_create_dto_1.scopes = None
    org_create_dto_1.clients = None

    org = organization_service.create_one(org_create_dto_1)
    _ = org_scopes_service.assigne_one(org.id, AuthorizationScope.CREATE)

    with pytest.raises(ConflictError):
        _ = org_scopes_service.assigne_one(org.id, AuthorizationScope.CREATE)


def test_unassinge_one_should_succeed(
    org_create_dto_1: OrganizationCreate,
    organization_service: OrganizationService,
    org_scopes_service: OrganizationScopesService,
) -> None:
    org_create_dto_1.scopes = [AuthorizationScope.CREATE]
    org_create_dto_1.clients = None

    org = organization_service.create_one(org_create_dto_1)
    org_scopes_service.unassigne_one(org.id, AuthorizationScope.CREATE)
    updated_org = organization_service.get_one(org.id)

    assert org.scopes is not None
    assert org.scopes[0].name == AuthorizationScope.CREATE.name
    assert updated_org.scopes is None


def test_unassinge_one_should_raise_when_org_not_found(
    org_scopes_service: OrganizationScopesService,
) -> None:
    with pytest.raises(RecordNotFoundError):
        org_scopes_service.unassigne_one(uuid4(), AuthorizationScope.LOCALIZE)


def test_unassinge_one_should_raise_when_scope_not_in_org(
    org_create_dto_1: OrganizationCreate,
    organization_service: OrganizationService,
    org_scopes_service: OrganizationScopesService,
) -> None:
    org_create_dto_1.scopes = None
    org_create_dto_1.clients = None

    org = organization_service.create_one(org_create_dto_1)

    assert org.scopes is None
    with pytest.raises(RecordNotFoundError):
        org_scopes_service.unassigne_one(org.id, AuthorizationScope.CREATE)


def test_unassigne_one_should_raise_when_client_uses_scope(
    org_create_dto_1: OrganizationCreate,
    organization_service: OrganizationService,
    org_scopes_service: OrganizationScopesService,
) -> None:
    org = organization_service.create_one(org_create_dto_1)

    assert org.scopes is not None
    assert AuthorizationScope.CREATE in org.scopes
    assert org.clients is not None
    client = org.clients[0]
    assert client.scopes is not None
    assert AuthorizationScope.CREATE in client.scopes

    with pytest.raises(ConflictError):
        org_scopes_service.unassigne_one(org.id, AuthorizationScope.CREATE)
