from uuid import uuid4

import pytest

from app.models.organization import OrganizationCreate
from app.models.scopes import AuthorizationScope
from app.services.exceptions import ConflictError, RecordNotFoundError
from app.services.organization import OrganizationService
from app.services.scopes.client_scopes import ClientScopesService


def test_assigne_one_should_succeed(
    org_create_dto_1: OrganizationCreate,
    organization_service: OrganizationService,
    client_scopes_service: ClientScopesService,
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    assert org.clients is not None
    client = org.clients[0]

    updated_client = client_scopes_service.assigne_one(org.id, client.id, AuthorizationScope.LOCALIZE)

    assert updated_client.scopes is not None
    assert client.scopes is not None
    assert AuthorizationScope.LOCALIZE not in client.scopes
    assert AuthorizationScope.LOCALIZE in updated_client.scopes


def test_assigne_one_should_raise_when_org_not_found(
    org_create_dto_1: OrganizationCreate,
    organization_service: OrganizationService,
    client_scopes_service: ClientScopesService,
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    assert org.clients is not None
    client = org.clients[0]

    with pytest.raises(RecordNotFoundError):
        _ = client_scopes_service.assigne_one(uuid4(), client.id, AuthorizationScope.LOCALIZE)


def test_assigne_one_should_raise_when_scope_not_in_org(
    org_create_dto_1: OrganizationCreate,
    organization_service: OrganizationService,
    client_scopes_service: ClientScopesService,
) -> None:
    org_create_dto_1.scopes = [AuthorizationScope.CREATE, AuthorizationScope.READ]
    assert org_create_dto_1.clients is not None
    org_create_dto_1.clients[0].scopes = None
    org = organization_service.create_one(org_create_dto_1)
    assert org.clients is not None
    client = org.clients[0]

    with pytest.raises(RecordNotFoundError):
        _ = client_scopes_service.assigne_one(org.id, client.id, AuthorizationScope.LOCALIZE)


def test_assigne_one_should_raise_when_client_is_not_found(
    org_create_dto_1: OrganizationCreate,
    organization_service: OrganizationService,
    client_scopes_service: ClientScopesService,
) -> None:
    org = organization_service.create_one(org_create_dto_1)

    with pytest.raises(RecordNotFoundError):
        _ = client_scopes_service.assigne_one(org.id, uuid4(), AuthorizationScope.LOCALIZE)


def test_assigne_one_should_raise_when_client_has_scopes(
    org_create_dto_1: OrganizationCreate,
    organization_service: OrganizationService,
    client_scopes_service: ClientScopesService,
) -> None:
    org_create_dto_1.scopes = [AuthorizationScope.CREATE, AuthorizationScope.READ]
    assert org_create_dto_1.clients is not None
    org_create_dto_1.clients[0].scopes = [AuthorizationScope.CREATE]

    org = organization_service.create_one(org_create_dto_1)
    assert org.clients is not None
    client = org.clients[0]

    with pytest.raises(ConflictError):
        _ = client_scopes_service.assigne_one(org.id, client.id, AuthorizationScope.CREATE)
