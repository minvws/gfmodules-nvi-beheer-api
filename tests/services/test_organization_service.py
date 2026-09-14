from uuid import UUID, uuid4

import pytest

from app.db.models.organization import OrganizationEntity
from app.db.repository.organization import OrganizationRepository
from app.db.repository.query_builder.context.organization_context import OrganizationQueryContext
from app.models.certificates import CertificateCreate
from app.models.client import ClientCreate
from app.models.oin import Oin
from app.models.organization import OrganizationCreate, OrganizationQueryParams
from app.models.source import SourceCreate
from app.models.ura import UraNumber
from app.services.certificate.organization_certificate import OrganizationCertificateService
from app.services.client import ClientService
from app.services.exceptions import (
    ConflictError,
    EntityHasActiveMemebersError,
    ForbidenOperationError,
    RecordNotFoundError,
    ScopeNotAllowedError,
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
)

SECOND_EXTERNAL_ID = UraNumber("87654321")
SECOND_ORG_NAME = "Second Test Organization"
SECON_SCOPES = "nvi:create nvi:localize"
SECOND_OIN = Oin("00000099000000002000")
SECOND_DOMAIN = "Other-Domain"
SECOND_CLIENT_NAME = "Test Client 2"


@pytest.fixture()
def org_dto_1() -> OrganizationCreate:
    return OrganizationCreate(
        external_id=TEST_EXTERNAL_ID,
        name=TEST_ORG_NAME,
        scopes=TEST_SCOPES,
        certificates=[
            CertificateCreate(organization_identifier=TEST_OIN, domain=TEST_DOMAIN),
            CertificateCreate(organization_identifier=SECOND_OIN, domain=SECOND_DOMAIN),
        ],
        sources=[
            SourceCreate(source_id="source-1", name="first source"),
            SourceCreate(source_id="source-2", name="second-source"),
        ],
        clients=[
            ClientCreate(
                name=TEST_CLIENT_NAME,
                scopes="nvi:create nvi:read",
                certificates=[
                    CertificateCreate(organization_identifier=TEST_OIN, domain=TEST_DOMAIN),
                ],
                sources=[
                    SourceCreate(source_id="source-1", name="first source"),
                ],
            ),
        ],
    )


@pytest.fixture()
def org_dto_2() -> OrganizationCreate:
    return OrganizationCreate(
        external_id=SECOND_EXTERNAL_ID,
        name=SECOND_ORG_NAME,
        scopes=SECON_SCOPES,
        sources=[SourceCreate(source_id="source-3", name="third-source")],
        clients=[
            ClientCreate(
                name=SECOND_CLIENT_NAME,
                scopes="nvi:localize",
                sources=[SourceCreate(source_id="source-3", name="third-source")],
            )
        ],
    )


def test_create_one_should_succeed(
    organization_service: OrganizationService,
    organization_entity: OrganizationEntity,
) -> None:
    dto = OrganizationCreate(
        external_id=organization_entity.external_id,
        name=organization_entity.name,
        scopes="nvi:create nvi:read nvi:delete nvi:localize",
    )

    actual = organization_service.create_one(dto)

    assert actual.external_id == dto.external_id
    assert actual.name == dto.name
    assert actual.sanitized_scopes is not None
    assert dto.sanitized_scopes is not None
    assert set(actual.sanitized_scopes) == set(dto.sanitized_scopes)
    assert actual.created_at is not None


def test_create_one_should_raise_with_unknown_scope(
    organization_service: OrganizationService,
    organization_entity: OrganizationEntity,
) -> None:
    unkown_scope = "nvi:some-scope"
    dto = OrganizationCreate(external_id=TEST_EXTERNAL_ID, name=TEST_ORG_NAME, scopes=unkown_scope)

    with pytest.raises(ScopeNotAllowedError) as exc:
        _ = organization_service.create_one(dto)

    assert f"Scope `{unkown_scope}` is not allowed" in exc.value.args


@pytest.mark.parametrize(
    "dto",
    [
        # org with sources and certificates
        OrganizationCreate(
            external_id=TEST_EXTERNAL_ID,
            name=TEST_ORG_NAME,
            scopes=TEST_SCOPES,
            sources=[SourceCreate(source_id=TEST_SOURCE_ID, name="some name")],
            certificates=[CertificateCreate(organization_identifier=TEST_OIN, domain=TEST_DOMAIN)],
        ),
        # org with sources and certs and plain client
        OrganizationCreate(
            external_id=TEST_EXTERNAL_ID,
            name=TEST_ORG_NAME,
            scopes=TEST_SCOPES,
            clients=[
                ClientCreate(
                    name=TEST_CLIENT_NAME,
                    description="some description",
                    scopes=TEST_SCOPES,
                )
            ],
            sources=[SourceCreate(source_id=TEST_SOURCE_ID, name="some name")],
            certificates=[CertificateCreate(organization_identifier=TEST_OIN, domain=TEST_DOMAIN)],
        ),
        # org with sources, certs and client with only certs
        OrganizationCreate(
            external_id=TEST_EXTERNAL_ID,
            name=TEST_ORG_NAME,
            scopes=TEST_SCOPES,
            clients=[
                ClientCreate(
                    name=TEST_CLIENT_NAME,
                    description="some description",
                    scopes=TEST_SCOPES,
                    certificates=[CertificateCreate(organization_identifier=TEST_OIN, domain=TEST_DOMAIN)],
                )
            ],
            sources=[SourceCreate(source_id=TEST_SOURCE_ID, name="some name")],
            certificates=[CertificateCreate(organization_identifier=TEST_OIN, domain=TEST_DOMAIN)],
        ),
        # org with sources and certs and client with sources
        OrganizationCreate(
            external_id=TEST_EXTERNAL_ID,
            name=TEST_ORG_NAME,
            scopes=TEST_SCOPES,
            clients=[
                ClientCreate(
                    name=TEST_CLIENT_NAME,
                    description="some description",
                    scopes=TEST_SCOPES,
                    sources=[SourceCreate(source_id=TEST_SOURCE_ID, name="some name")],
                )
            ],
            sources=[SourceCreate(source_id=TEST_SOURCE_ID, name="some name")],
            certificates=[CertificateCreate(organization_identifier=TEST_OIN, domain=TEST_DOMAIN)],
        ),
        # org complete and client complete
        OrganizationCreate(
            external_id=TEST_EXTERNAL_ID,
            name=TEST_ORG_NAME,
            scopes=TEST_SCOPES,
            clients=[
                ClientCreate(
                    name=TEST_CLIENT_NAME,
                    description="some description",
                    scopes=TEST_SCOPES,
                    sources=[SourceCreate(source_id=TEST_SOURCE_ID, name="some name")],
                    certificates=[CertificateCreate(organization_identifier=TEST_OIN, domain=TEST_DOMAIN)],
                )
            ],
            sources=[SourceCreate(source_id=TEST_SOURCE_ID, name="some name")],
            certificates=[CertificateCreate(organization_identifier=TEST_OIN, domain=TEST_DOMAIN)],
        ),
    ],
)
def test_create_should_succeed_with_complex_object(
    organization_service: OrganizationService,
    organization_certificate_service: OrganizationCertificateService,
    organization_source_service: OrganizationSourceService,
    client_service: ClientService,
    dto: OrganizationCreate,
) -> None:
    actual = organization_service.create_one(dto)

    assert actual.id is not None
    assert isinstance(actual.id, UUID)
    assert actual.external_id == dto.external_id
    assert actual.name == dto.name
    if actual.sanitized_scopes:
        assert dto.sanitized_scopes is not None
        assert set(actual.sanitized_scopes) == set(dto.sanitized_scopes)

    if actual.certificates:
        for expected_org_cert in actual.certificates:
            actual_org_cert = organization_certificate_service.get_one(expected_org_cert.id, actual.id)
            assert expected_org_cert == actual_org_cert

    if actual.sources:
        for expected_org_src in actual.sources:
            actual_org_src = organization_source_service.get_one(actual.id, expected_org_src.id)
            assert expected_org_src == actual_org_src

    if actual.clients:
        for expected_client in actual.clients:
            actual_client = client_service.get_one(expected_client.id, actual.id)
            assert actual_client.id == expected_client.id
            if actual_client.scopes:
                assert expected_client.scopes is not None
                assert [s for s in expected_client.scopes].sort() == [s for s in expected_client.scopes].sort()

            assert actual_client.certificates == expected_client.certificates
            assert actual_client.sources == expected_client.sources


def test_create_one_should_raise_when_source_id_exists(organization_service: OrganizationService) -> None:
    source_dto = SourceCreate(source_id=TEST_SOURCE_ID, name="some name")
    org_dto_1 = OrganizationCreate(external_id=TEST_EXTERNAL_ID, name=TEST_ORG_NAME, sources=[source_dto])
    org_dto_2 = OrganizationCreate(external_id=UraNumber("90002001"), name="org-2", sources=[source_dto])

    _ = organization_service.create_one(org_dto_1)

    with pytest.raises(ConflictError) as exc:
        _ = organization_service.create_one(org_dto_2)

    assert f"Sources with source_id {source_dto.source_id} already exists" in exc.value.args


def test_create_one_should_raise_when_client_scope_does_not_match_org(
    organization_service: OrganizationService,
) -> None:
    org_scopes = "nvi:create nvi:delete"
    client_scope = "nvi:read nvi:localize"
    dto = OrganizationCreate(
        external_id=TEST_EXTERNAL_ID,
        name=TEST_ORG_NAME,
        scopes=org_scopes,
        clients=[ClientCreate(name=TEST_CLIENT_NAME, scopes=client_scope)],
    )
    with pytest.raises(ScopesNotGrantedError):
        _ = organization_service.create_one(dto)


@pytest.mark.parametrize(
    "dto",
    [
        OrganizationCreate(
            external_id=TEST_EXTERNAL_ID,
            name=TEST_ORG_NAME,
            certificates=[CertificateCreate(organization_identifier=TEST_OIN, domain=TEST_DOMAIN)],
            sources=[SourceCreate(source_id="source-1", name="test source")],
            clients=[
                ClientCreate(
                    name=TEST_CLIENT_NAME,
                    certificates=[
                        CertificateCreate(organization_identifier=Oin("00000099000000002000"), domain="other-domain")
                    ],
                )
            ],
        ),
        OrganizationCreate(
            external_id=TEST_EXTERNAL_ID,
            name=TEST_ORG_NAME,
            certificates=[CertificateCreate(organization_identifier=TEST_OIN, domain=TEST_DOMAIN)],
            sources=[SourceCreate(source_id="source-1", name="test source")],
            clients=[
                ClientCreate(name=TEST_CLIENT_NAME, sources=[SourceCreate(source_id="source-2", name="test source 2")])
            ],
        ),
    ],
)
def test_create_one_should_raise_with_sources_and_certificate_are_not_subset_of_org(
    organization_service: OrganizationService, dto: OrganizationCreate
) -> None:
    with pytest.raises(ForbidenOperationError):
        _ = organization_service.create_one(dto)


def test_get_one_should_succeed(
    organization_service: OrganizationService,
) -> None:
    dto = OrganizationCreate(
        external_id=TEST_EXTERNAL_ID,
        name=TEST_ORG_NAME,
        scopes=TEST_SCOPES,
        clients=[
            ClientCreate(
                name=TEST_CLIENT_NAME,
                description="some description",
                scopes=TEST_SCOPES,
                sources=[SourceCreate(source_id=TEST_SOURCE_ID, name="some name")],
                certificates=[CertificateCreate(organization_identifier=TEST_OIN, domain=TEST_DOMAIN)],
            )
        ],
        sources=[SourceCreate(source_id=TEST_SOURCE_ID, name="some name")],
        certificates=[CertificateCreate(organization_identifier=TEST_OIN, domain=TEST_DOMAIN)],
    )

    expected = organization_service.create_one(dto)

    actual = organization_service.get_one(expected.id)

    assert expected == actual


def test_get_one_should_raise_when_not_found(organization_service: OrganizationService) -> None:
    dummy_id = uuid4()
    dto = OrganizationCreate(external_id=TEST_EXTERNAL_ID, name=TEST_ORG_NAME)

    _ = organization_service.create_one(dto)

    with pytest.raises(RecordNotFoundError) as exc:
        _ = organization_service.get_one(dummy_id)

    assert f"Record {dummy_id} not found" in exc.value.args


def test_delete_one_should_succeed_and_perform_soft_delete(
    organization_service: OrganizationService, organization_repository: OrganizationRepository
) -> None:
    dto = OrganizationCreate(external_id=TEST_EXTERNAL_ID, name=TEST_ORG_NAME)
    org = organization_service.create_one(dto)

    organization_service.delete_one(org.id)

    with organization_repository.db_session:
        deleted_org = organization_repository.find(
            OrganizationQueryContext(external_id=org.external_id), include_delete=True
        )

    assert org is not None
    assert deleted_org is not None
    assert deleted_org.deleted_at is not None


def delete_one_raises_when_not_found(organization_service: OrganizationService) -> None:
    dto = OrganizationCreate(external_id=TEST_EXTERNAL_ID, name=TEST_ORG_NAME)
    _ = organization_service.create_one(dto)

    with pytest.raises(RecordNotFoundError):
        organization_service.delete_one(uuid4())


@pytest.mark.parametrize(
    "dto",
    [
        # org with sources and certs
        OrganizationCreate(
            external_id=TEST_EXTERNAL_ID,
            name=TEST_ORG_NAME,
            scopes=TEST_SCOPES,
            sources=[SourceCreate(source_id=TEST_SOURCE_ID, name="some name")],
            certificates=[CertificateCreate(organization_identifier=TEST_OIN, domain=TEST_DOMAIN)],
        ),
        # org with clients
        OrganizationCreate(
            external_id=TEST_EXTERNAL_ID,
            name=TEST_ORG_NAME,
            scopes=TEST_SCOPES,
            clients=[
                ClientCreate(
                    name=TEST_CLIENT_NAME,
                    description="some description",
                    scopes=TEST_SCOPES,
                )
            ],
        ),
        # org with sources, certs and clients
        OrganizationCreate(
            external_id=TEST_EXTERNAL_ID,
            name=TEST_ORG_NAME,
            scopes=TEST_SCOPES,
            clients=[
                ClientCreate(
                    name=TEST_CLIENT_NAME,
                    description="some description",
                    scopes=TEST_SCOPES,
                    certificates=[CertificateCreate(organization_identifier=TEST_OIN, domain=TEST_DOMAIN)],
                )
            ],
            certificates=[CertificateCreate(organization_identifier=TEST_OIN, domain=TEST_DOMAIN)],
        ),
        # org with sources and clients
        OrganizationCreate(
            external_id=TEST_EXTERNAL_ID,
            name=TEST_ORG_NAME,
            scopes=TEST_SCOPES,
            clients=[
                ClientCreate(
                    name=TEST_CLIENT_NAME,
                    description="some description",
                    scopes=TEST_SCOPES,
                    sources=[SourceCreate(source_id=TEST_SOURCE_ID, name="some name")],
                )
            ],
            sources=[SourceCreate(source_id=TEST_SOURCE_ID, name="some name")],
        ),
        # org complete and client complete
        OrganizationCreate(
            external_id=TEST_EXTERNAL_ID,
            name=TEST_ORG_NAME,
            scopes=TEST_SCOPES,
            clients=[
                ClientCreate(
                    name=TEST_CLIENT_NAME,
                    description="some description",
                    scopes=TEST_SCOPES,
                    sources=[SourceCreate(source_id=TEST_SOURCE_ID, name="some name")],
                    certificates=[CertificateCreate(organization_identifier=TEST_OIN, domain=TEST_DOMAIN)],
                )
            ],
            sources=[SourceCreate(source_id=TEST_SOURCE_ID, name="some name")],
            certificates=[CertificateCreate(organization_identifier=TEST_OIN, domain=TEST_DOMAIN)],
        ),
    ],
)
def test_delete_one_rejects_when_active_members_exist(
    organization_service: OrganizationService, dto: OrganizationCreate
) -> None:
    org = organization_service.create_one(dto)

    with pytest.raises(EntityHasActiveMemebersError):
        organization_service.delete_one(org.id)


def test_get_many_should_return_all(
    organization_service: OrganizationService,
    org_dto_1: OrganizationCreate,
    org_dto_2: OrganizationCreate,
) -> None:

    _ = organization_service.create_one(org_dto_1)
    _ = organization_service.create_one(org_dto_2)

    actual = organization_service.get_many(OrganizationQueryParams())

    assert len(actual) == 2


@pytest.mark.parametrize(
    "params",
    [
        OrganizationQueryParams(name=TEST_ORG_NAME),
        OrganizationQueryParams(external_id=TEST_EXTERNAL_ID),
        OrganizationQueryParams(scopes="nvi:delete"),
    ],
)
def test_get_many_should_filter_on_org_attr(
    organization_service: OrganizationService,
    org_dto_1: OrganizationCreate,
    org_dto_2: OrganizationCreate,
    params: OrganizationQueryParams,
) -> None:
    org = organization_service.create_one(org_dto_1)
    _ = organization_service.create_one(org_dto_2)

    expected = [organization_service.get_one(org.id)]
    actual = organization_service.get_many(params)

    assert expected == actual


def test_update_one_should_succeed(organization_service: OrganizationService, dto: OrganizationCreate) -> None: ...


#
# def test_update_one_returns_none_when_not_found(
#     organization_service: OrganizationService,
# ) -> None:
#     result = organization_service.update_one(uuid4(), name="not-found")
#     assert result is None
