from uuid import uuid4

import pytest

from app import utils
from app.models.certificates import CertificateCreate, CertificateQueryParams, CertificateUpdate
from app.models.client import ClientCreate, ClientQueryParams, ClientUpdate
from app.models.organization import OrganizationCreate
from app.models.source import SourceCreate, SourceQueryParams, SourceUpdate
from app.services.certificate.organization_certificate import OrganizationCertificateService
from app.services.client import ClientService
from app.services.exceptions import (
    EntityHasActiveMemebersError,
    ForbidenOperationError,
    RecordNotFoundError,
    ScopesNotGrantedError,
)
from app.services.organization import OrganizationService
from app.services.source.organization_source import OrganizationSourceService
from tests.conftest import (
    TEST_CLIENT_NAME,
    TEST_DOMAIN,
    TEST_EXTERNAL_ID,
    TEST_OIN,
    TEST_ORG_NAME,
    TEST_SCOPES,
    TEST_SOURCE_ID,
    TEST_SOURCE_NAME,
)


@pytest.mark.parametrize(
    "org_dto, client_dto",
    [
        (
            OrganizationCreate(
                external_id=TEST_EXTERNAL_ID,
                name=TEST_ORG_NAME,
            ),
            ClientCreate(name=TEST_CLIENT_NAME),
        ),
        (
            OrganizationCreate(
                external_id=TEST_EXTERNAL_ID, name=TEST_ORG_NAME, scopes="nvi:create nvi:read nvi:delete"
            ),
            ClientCreate(name=TEST_CLIENT_NAME, scopes="nvi:create nvi:read"),
        ),
        (
            OrganizationCreate(
                external_id=TEST_EXTERNAL_ID,
                name=TEST_ORG_NAME,
                certificates=[CertificateCreate(organization_identifier=TEST_OIN, domain=TEST_DOMAIN)],
            ),
            ClientCreate(name=TEST_CLIENT_NAME),
        ),
        (
            OrganizationCreate(
                external_id=TEST_EXTERNAL_ID,
                name=TEST_ORG_NAME,
                certificates=[CertificateCreate(organization_identifier=TEST_OIN, domain=TEST_DOMAIN)],
            ),
            ClientCreate(
                name=TEST_CLIENT_NAME,
                certificates=[CertificateCreate(organization_identifier=TEST_OIN, domain=TEST_DOMAIN)],
            ),
        ),
        (
            OrganizationCreate(
                external_id=TEST_EXTERNAL_ID,
                name=TEST_ORG_NAME,
                sources=[SourceCreate(source_id=TEST_SOURCE_ID, name=TEST_SOURCE_NAME)],
            ),
            ClientCreate(
                name=TEST_CLIENT_NAME,
            ),
        ),
        (
            OrganizationCreate(
                external_id=TEST_EXTERNAL_ID,
                name=TEST_ORG_NAME,
                sources=[SourceCreate(source_id=TEST_SOURCE_ID, name=TEST_SOURCE_NAME)],
            ),
            ClientCreate(
                name=TEST_CLIENT_NAME, sources=[SourceCreate(source_id=TEST_SOURCE_ID, name=TEST_SOURCE_NAME)]
            ),
        ),
        (
            OrganizationCreate(
                external_id=TEST_EXTERNAL_ID,
                name=TEST_ORG_NAME,
                sources=[SourceCreate(source_id=TEST_SOURCE_ID, name=TEST_SOURCE_NAME)],
                certificates=[CertificateCreate(organization_identifier=TEST_OIN, domain=TEST_DOMAIN)],
            ),
            ClientCreate(
                name=TEST_CLIENT_NAME,
                sources=[SourceCreate(source_id=TEST_SOURCE_ID, name=TEST_SOURCE_NAME)],
                certificates=[CertificateCreate(organization_identifier=TEST_OIN, domain=TEST_DOMAIN)],
            ),
        ),
    ],
)
def test_create_one_should_succeed(
    client_service: ClientService,
    organization_service: OrganizationService,
    org_dto: OrganizationCreate,
    client_dto: ClientCreate,
) -> None:

    org = organization_service.create_one(org_dto)
    client = client_service.create_one(org.id, client_dto)

    assert client.organization_id == org.id
    assert utils.is_subset(
        [s.id for s in org.sources] if org.sources else [],
        [s.id for s in client.sources] if client.sources else [],
    )
    assert utils.is_subset(
        [c.id for c in org.certificates] if org.certificates else [],
        [c.id for c in client.certificates] if client.certificates else [],
    )
    if org.scopes and client.scopes:
        assert utils.is_subset(org.scopes.split(" "), client.scopes.split(" "))


def test_create_should_raise_when_mismatch_scopes(
    client_service: ClientService,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
    client_create_dto_1: ClientCreate,
) -> None:
    org_create_dto_1.clients = None
    org_create_dto_1.scopes = "nvi:create nvi:delete nvi:localize"
    client_create_dto_1.scopes = "nvi:read"

    org = organization_service.create_one(org_create_dto_1)

    with pytest.raises(ScopesNotGrantedError):
        _ = client_service.create_one(org.id, client_create_dto_1)


@pytest.mark.parametrize(
    "org_dto, client_dto",
    [
        (
            OrganizationCreate(
                external_id=TEST_EXTERNAL_ID,
                name=TEST_ORG_NAME,
                sources=[SourceCreate(source_id=TEST_SOURCE_ID, name=TEST_SOURCE_NAME)],
            ),
            ClientCreate(
                name=TEST_CLIENT_NAME,
                certificates=[CertificateCreate(organization_identifier=TEST_OIN, domain=TEST_DOMAIN)],
            ),
        ),
        (
            OrganizationCreate(
                external_id=TEST_EXTERNAL_ID,
                name=TEST_ORG_NAME,
                certificates=[CertificateCreate(organization_identifier=TEST_OIN, domain=TEST_DOMAIN)],
            ),
            ClientCreate(
                name=TEST_CLIENT_NAME,
                sources=[SourceCreate(source_id=TEST_SOURCE_ID, name=TEST_SOURCE_NAME)],
            ),
        ),
        (
            OrganizationCreate(
                external_id=TEST_EXTERNAL_ID,
                name=TEST_ORG_NAME,
            ),
            ClientCreate(
                name=TEST_CLIENT_NAME,
                sources=[SourceCreate(source_id=TEST_SOURCE_ID, name=TEST_SOURCE_NAME)],
                certificates=[CertificateCreate(organization_identifier=TEST_OIN, domain=TEST_DOMAIN)],
            ),
        ),
    ],
)
def test_create_should_raise_on_cert_and_source_mismatch(
    organization_service: OrganizationService,
    client_service: ClientService,
    org_dto: OrganizationCreate,
    client_dto: ClientCreate,
) -> None:
    org = organization_service.create_one(org_dto)

    with pytest.raises(ForbidenOperationError):
        _ = client_service.create_one(org.id, client_dto)


def test_get_one_should_succeed(
    client_service: ClientService, organization_service: OrganizationService, org_create_dto_1: OrganizationCreate
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    assert org.clients is not None
    client = org.clients[0]

    actual = client_service.get_one(client.id, org.id)

    assert actual == client


def test_get_one_should_raise_on_wrong_client_id(
    client_service: ClientService, organization_service: OrganizationService, org_create_dto_1: OrganizationCreate
) -> None:
    org = organization_service.create_one(org_create_dto_1)

    with pytest.raises(RecordNotFoundError):
        _ = client_service.get_one(uuid4(), org.id)


def test_get_one_should_raise_on_org_client_id(
    client_service: ClientService, organization_service: OrganizationService, org_create_dto_1: OrganizationCreate
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    assert org.clients is not None
    client = org.clients[0]

    with pytest.raises(RecordNotFoundError):
        _ = client_service.get_one(client.id, uuid4())


def test_get_many_should_succeed(
    client_service: ClientService,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
    org_create_dto_2: OrganizationCreate,
) -> None:

    org = organization_service.create_one(org_create_dto_1)
    org_2 = organization_service.create_one(org_create_dto_2)

    result_1 = client_service.get_many(org.id, ClientQueryParams())
    result_2 = client_service.get_many(org_2.id, ClientQueryParams())

    assert org.clients is not None
    assert result_1 == org.clients
    assert org_2.clients is not None
    assert result_2 == org_2.clients


def test_get_many_should_return_empty_list_on_no_match(
    client_service: ClientService,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
) -> None:
    org = organization_service.create_one(org_create_dto_1)

    actual = client_service.get_many(org.id, ClientQueryParams(name="some-name"))

    assert actual == []


@pytest.mark.parametrize(
    "params",
    [
        ClientQueryParams(name=TEST_CLIENT_NAME),
        ClientQueryParams(scopes=TEST_SCOPES),
        ClientQueryParams(cert_organization_identifier=TEST_OIN),
        ClientQueryParams(cert_domain=TEST_DOMAIN),
        ClientQueryParams(cert_organization_identifier=TEST_OIN, cert_domain=TEST_DOMAIN),
        ClientQueryParams(source_id=TEST_SOURCE_ID),
        ClientQueryParams(source_name=TEST_SOURCE_NAME),
        ClientQueryParams(source_id=TEST_SOURCE_ID, source_name=TEST_SOURCE_NAME),
    ],
)
def test_get_many_should_return_according_based_on_params(
    client_service: ClientService,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
    org_create_dto_2: OrganizationCreate,
    params: ClientQueryParams,
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    org_2 = organization_service.create_one(org_create_dto_2)

    result = client_service.get_many(org.id, params)

    assert org.clients is not None
    assert result == org.clients
    assert org_2.clients is not None
    assert [c.id for c in org_2.clients] not in [c.id for c in org.clients]


def test_get_many_should_return_on_deleted_flag(
    client_service: ClientService,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
) -> None:
    assert org_create_dto_1.clients is not None
    org_create_dto_1.clients[0].certificates = None
    org_create_dto_1.clients[0].sources = None
    org_1 = organization_service.create_one(org_create_dto_1)

    assert org_1.clients is not None
    client_1 = org_1.clients[0]
    client_service.delete_one(client_1.id, org_1.id)

    actual_with_deleted_flag = client_service.get_many(org_1.id, ClientQueryParams(include_deleted=True))
    actual_not_deleted_flag = client_service.get_many(org_1.id, ClientQueryParams())

    assert len(actual_with_deleted_flag) == 1
    assert client_1.id in [c.id for c in actual_with_deleted_flag]
    assert actual_not_deleted_flag == []


def test_update_one_should_succeed(
    client_service: ClientService,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
    cert_create_dto_1: CertificateCreate,
    source_create_dto_1: SourceCreate,
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    create_dto = ClientCreate(
        name="old_name", certificates=[cert_create_dto_1], sources=[source_create_dto_1], scopes="nvi:create"
    )
    new_client = client_service.create_one(org.id, create_dto)
    update_dto = ClientUpdate(id=new_client.id, name="new_name")
    actual = client_service.update_one(new_client.id, org.id, update_dto)

    assert actual.id == update_dto.id
    assert actual.name == update_dto.name
    assert actual.certificates is None
    assert actual.sources is None


def test_update_one_should_add_sources_to_client(
    client_service: ClientService,
    organization_service: OrganizationService,
    organization_source_service: OrganizationSourceService,
    org_create_dto_1: OrganizationCreate,
    cert_create_dto_1: CertificateCreate,
    source_create_dto_1: SourceCreate,
    source_create_dto_2: SourceCreate,
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    sources = organization_source_service.get_many(org.id, SourceQueryParams())
    sources_dto = [SourceUpdate(id=s.id, source_id=s.source_id, name=s.name) for s in sources]
    create_dto = ClientCreate(
        name="old_name", certificates=[cert_create_dto_1], sources=[source_create_dto_1], scopes="nvi:create"
    )
    new_client = client_service.create_one(org.id, create_dto)
    update_dto = ClientUpdate(id=new_client.id, name="new_name", sources=sources_dto)

    actual = client_service.update_one(new_client.id, org.id, update_dto)

    assert actual.id == update_dto.id
    assert actual.name == update_dto.name
    assert actual.certificates is None
    assert actual.sources is not None
    assert len(actual.sources) == 2


def test_update_one_should_swap_sources_to_client(
    client_service: ClientService,
    organization_service: OrganizationService,
    organization_source_service: OrganizationSourceService,
    org_create_dto_1: OrganizationCreate,
    cert_create_dto_1: CertificateCreate,
    source_create_dto_1: SourceCreate,
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    assert org.sources is not None
    src_to_swap = org.sources[1]
    src_update_dto = SourceUpdate(**src_to_swap.model_dump())
    create_dto = ClientCreate(
        name="old_name", certificates=[cert_create_dto_1], sources=[source_create_dto_1], scopes="nvi:create"
    )
    new_client = client_service.create_one(org.id, create_dto)
    update_dto = ClientUpdate(id=new_client.id, name="new name", sources=[src_update_dto])

    actual = client_service.update_one(new_client.id, org.id, update_dto)

    assert actual.id == update_dto.id
    assert actual.certificates is None
    assert actual.sources is not None
    assert len(actual.sources) == 1
    assert actual.sources[0].id == src_to_swap.id


def test_update_one_should_add_certificates_to_client(
    client_service: ClientService,
    organization_service: OrganizationService,
    organization_certificate_service: OrganizationCertificateService,
    org_create_dto_1: OrganizationCreate,
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    certs_to_add = organization_certificate_service.get_many(org.id, CertificateQueryParams())
    certs_dto = [
        CertificateUpdate(id=c.id, organization_identifier=c.organization_identifier, domain=c.domain)
        for c in certs_to_add
    ]
    create_dto = ClientCreate(name="old_name", scopes="nvi:create")
    new_client = client_service.create_one(org.id, create_dto)
    update_dto = ClientUpdate(id=new_client.id, name="new name", certificates=certs_dto)

    actual = client_service.update_one(new_client.id, org.id, update_dto)

    assert actual.sources is None
    assert actual.certificates is not None
    assert len(actual.certificates) == 2
    assert actual.certificates == certs_to_add


def test_update_one_should_raise_when_source_not_in_org(
    client_service: ClientService,
    organization_service: OrganizationService,
    organization_certificate_service: OrganizationCertificateService,
    org_create_dto_1: OrganizationCreate,
    source_create_dto_1: SourceCreate,
    source_create_dto_2: SourceCreate,
) -> None:
    org_create_dto_1.sources = [source_create_dto_1]
    org_create_dto_1.clients = None
    org = organization_service.create_one(org_create_dto_1)
    create_dto = ClientCreate(name="old_name", scopes="nvi:create")
    new_client = client_service.create_one(org.id, create_dto)
    update_dto = ClientUpdate(
        id=new_client.id, name="new name", sources=[SourceUpdate(**source_create_dto_2.model_dump(), id=uuid4())]
    )

    with pytest.raises(ForbidenOperationError):
        _ = client_service.update_one(new_client.id, org.id, update_dto)


def test_upate_one_should_swap_certificates(
    client_service: ClientService,
    organization_service: OrganizationService,
    organization_certificate_service: OrganizationCertificateService,
    org_create_dto_1: OrganizationCreate,
    cert_create_dto_1: CertificateCreate,
    cert_create_dto_2: CertificateCreate,
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    assert org.certificates is not None
    cert_to_swap = org.certificates[1]
    cert_dto = CertificateUpdate(**cert_to_swap.model_dump())
    create_dto = ClientCreate(name="old_name", scopes="nvi:create", certificates=[cert_create_dto_1])
    new_client = client_service.create_one(org.id, create_dto)
    update_dto = ClientUpdate(id=new_client.id, name="new name", certificates=[cert_dto])

    actual = client_service.update_one(new_client.id, org.id, update_dto)

    assert actual.sources is None
    assert actual.certificates is not None
    assert len(actual.certificates) == 1
    assert org.certificates[0].id not in [c.id for c in actual.certificates]
    assert actual.certificates[0].id == cert_dto.id


def test_update_one_should_raise_when_adding_cert_not_in_org(
    client_service: ClientService,
    organization_service: OrganizationService,
    organization_certificate_service: OrganizationCertificateService,
    org_create_dto_1: OrganizationCreate,
    cert_create_dto_1: CertificateCreate,
    cert_create_dto_2: CertificateCreate,
) -> None:
    org_create_dto_1.certificates = [cert_create_dto_1]
    org = organization_service.create_one(org_create_dto_1)
    client_dto = ClientCreate(name="old name", certificates=[cert_create_dto_1])
    new_client = client_service.create_one(org.id, client_dto)
    cert_dto = CertificateUpdate(id=uuid4(), **cert_create_dto_2.model_dump())
    update_dto = ClientUpdate(id=new_client.id, name="new name", certificates=[cert_dto])

    with pytest.raises(ForbidenOperationError):
        _ = client_service.update_one(new_client.id, org.id, update_dto)


def test_update_one_should_successfully_change_scope(
    client_service: ClientService, organization_service: OrganizationService, org_create_dto_1: OrganizationCreate
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    create_dto = ClientCreate(name="old_name", scopes="nvi:create")
    new_client = client_service.create_one(org.id, create_dto)
    update_dto = ClientUpdate(id=new_client.id, name="new name", scopes="nvi:read nvi:delete")

    actual = client_service.update_one(new_client.id, org.id, update_dto)

    assert actual.id == update_dto.id
    assert " ".split(actual.scopes) == " ".split(update_dto.scopes)


def test_update_one_should_raise_with_scope_not_in_org(
    client_service: ClientService, organization_service: OrganizationService, org_create_dto_1: OrganizationCreate
) -> None:
    org_create_dto_1.scopes = "nvi:create nvi:read"
    org = organization_service.create_one(org_create_dto_1)
    create_dto = ClientCreate(name="old_name", scopes="nvi:create")
    new_client = client_service.create_one(org.id, create_dto)
    update_dto = ClientUpdate(id=new_client.id, name="new name", scopes="nvi:delete")

    with pytest.raises(ScopesNotGrantedError):
        _ = client_service.update_one(new_client.id, org.id, update_dto)


def test_delete_one_should_succeed(
    client_service: ClientService, organization_service: OrganizationService, org_create_dto_1: OrganizationCreate
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    dto = ClientCreate(name="some name")
    new_client = client_service.create_one(org.id, dto)

    client_service.delete_one(new_client.id, org.id)

    with pytest.raises(RecordNotFoundError):
        _ = client_service.get_one(new_client.id, org.id)


def test_delete_one_should_raise_with_unkown_org(
    client_service: ClientService, organization_service: OrganizationService, org_create_dto_1: OrganizationCreate
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    dto = ClientCreate(name="some name")
    new_client = client_service.create_one(org.id, dto)

    with pytest.raises(RecordNotFoundError):
        client_service.delete_one(new_client.id, uuid4())


def test_delete_one_should_raise_with_unkown_client(
    client_service: ClientService, organization_service: OrganizationService, org_create_dto_1: OrganizationCreate
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    dto = ClientCreate(name="some name")
    _ = client_service.create_one(org.id, dto)

    with pytest.raises(RecordNotFoundError):
        client_service.delete_one(uuid4(), org.id)


@pytest.mark.parametrize(
    "dto",
    [
        ClientCreate(name="some-name", sources=[SourceCreate(source_id=TEST_SOURCE_ID, name=TEST_CLIENT_NAME)]),
        ClientCreate(
            name="some-name", certificates=[CertificateCreate(organization_identifier=TEST_OIN, domain=TEST_DOMAIN)]
        ),
        ClientCreate(
            name="some-name",
            sources=[SourceCreate(source_id=TEST_SOURCE_ID, name=TEST_CLIENT_NAME)],
            certificates=[CertificateCreate(organization_identifier=TEST_OIN, domain=TEST_DOMAIN)],
        ),
    ],
)
def test_delete_one_should_raise_when_client_has_active_memebers(
    client_service: ClientService,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
    dto: ClientCreate,
) -> None:

    org = organization_service.create_one(org_create_dto_1)
    new_client = client_service.create_one(org.id, dto)

    with pytest.raises(EntityHasActiveMemebersError):
        client_service.delete_one(new_client.id, org.id)
