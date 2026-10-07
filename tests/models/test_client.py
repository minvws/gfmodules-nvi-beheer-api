from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.certificates import CertificateCreate
from app.models.client import (
    ClientCreate,
    ClientQueryParams,
    ClientResolveRequest,
    ClientResolveResponse,
    ClientUpdate,
)
from app.models.oin import Oin
from app.models.scopes import AuthorizationScope
from app.models.source import SourceCreate
from app.models.ura import UraNumber
from tests.conftest import (
    SECOND_DOMAIN,
    SECOND_OIN,
    TEST_CLIENT_NAME,
    TEST_DOMAIN,
    TEST_EXTERNAL_ID,
    TEST_OIN,
    TEST_ORG_NAME,
)


def test_create_should_succeed(cert_create_dto_1: CertificateCreate, source_create_dto_1: SourceCreate) -> None:
    model = ClientCreate(name=TEST_CLIENT_NAME, certificates=[cert_create_dto_1], sources=[source_create_dto_1])
    assert model.name == TEST_CLIENT_NAME
    assert model.sources is not None
    assert model.certificates is not None
    assert model.certificates == [cert_create_dto_1]
    assert model.sources == [source_create_dto_1]


def test_create_with_scopes_should_succeed() -> None:
    model = ClientCreate(name="Test Client", scopes=[AuthorizationScope("nvi:read")])
    assert model.scopes == [AuthorizationScope("nvi:read")]
    assert model.sources is None
    assert model.certificates is None


@pytest.mark.parametrize(
    "certificates",
    [
        None,
        [],
        [CertificateCreate(organization_identifier=TEST_OIN, domain=TEST_DOMAIN)],
        [
            CertificateCreate(organization_identifier=TEST_OIN, domain=TEST_DOMAIN),
            CertificateCreate(organization_identifier=TEST_OIN, domain=SECOND_DOMAIN),
        ],
        [
            CertificateCreate(organization_identifier=TEST_OIN, domain=TEST_DOMAIN),
            CertificateCreate(organization_identifier=SECOND_OIN, domain=TEST_DOMAIN),
        ],
        [
            CertificateCreate(organization_identifier=TEST_OIN, domain=TEST_DOMAIN),
            CertificateCreate(organization_identifier=TEST_OIN, domain=TEST_DOMAIN.upper()),
        ],
    ],
)
def test_create_with_unique_certificates_should_succeed(certificates: list[CertificateCreate] | None) -> None:
    model = ClientCreate(name=TEST_CLIENT_NAME, certificates=certificates)

    assert model.certificates == certificates


@pytest.mark.parametrize(
    "certificate_pairs, duplicate_values",
    [
        ([(TEST_OIN, TEST_DOMAIN), (TEST_OIN, TEST_DOMAIN)], f"{TEST_OIN}/{TEST_DOMAIN}"),
        (
            [
                (SECOND_OIN, SECOND_DOMAIN),
                (TEST_OIN, TEST_DOMAIN),
                (SECOND_OIN, SECOND_DOMAIN),
                (TEST_OIN, "unique.example"),
                (TEST_OIN, TEST_DOMAIN),
                (SECOND_OIN, SECOND_DOMAIN),
            ],
            f"{SECOND_OIN}/{SECOND_DOMAIN} {TEST_OIN}/{TEST_DOMAIN}",
        ),
    ],
)
def test_create_with_duplicate_certificates_should_raise(
    certificate_pairs: list[tuple[Oin, str]], duplicate_values: str
) -> None:
    certificates = [
        CertificateCreate(organization_identifier=Oin(str(identifier)), domain=domain)
        for identifier, domain in certificate_pairs
    ]

    with pytest.raises(ValidationError) as exc:
        ClientCreate(name=TEST_CLIENT_NAME, certificates=certificates)

    errors = exc.value.errors()
    assert len(errors) == 1
    assert errors[0]["loc"] == ("certificates",)
    assert errors[0]["type"] == "value_error"
    assert errors[0]["msg"] == f"Value error, Duplicate certificate values: {duplicate_values}"


@pytest.mark.parametrize(
    "sources",
    [
        None,
        [],
        [SourceCreate(source_id="source-1", name="Source 1")],
        [
            SourceCreate(source_id="source-1", name="Source 1"),
            SourceCreate(source_id="source-2", name="Source 2"),
        ],
        [
            SourceCreate(source_id="source-A", name="Source A"),
            SourceCreate(source_id="source-a", name="Source a"),
        ],
    ],
)
def test_create_with_unique_sources_should_succeed(sources: list[SourceCreate] | None) -> None:
    model = ClientCreate(name=TEST_CLIENT_NAME, sources=sources)

    assert model.sources == sources


@pytest.mark.parametrize(
    "source_ids, duplicate_ids",
    [
        (["source-1", "source-1"], "source-1"),
        (["source-2", "source-1", "source-2", "unique", "source-1", "source-2"], "source-2 source-1"),
    ],
)
def test_create_with_duplicate_source_ids_should_raise(source_ids: list[str], duplicate_ids: str) -> None:
    sources = [SourceCreate(source_id=source_id, name=f"Source {index}") for index, source_id in enumerate(source_ids)]

    with pytest.raises(ValidationError) as exc:
        ClientCreate(name=TEST_CLIENT_NAME, sources=sources)

    errors = exc.value.errors()
    assert len(errors) == 1
    assert errors[0]["loc"] == ("sources",)
    assert errors[0]["type"] == "value_error"
    assert errors[0]["msg"] == f"Value error, Duplicate source_id values: {duplicate_ids}"


def test_create_missing_name_should_raise() -> None:
    with pytest.raises(ValidationError):
        ClientCreate(description="some desc")  # type: ignore[call-arg]


def test_update_is_partial_all_fields_optional() -> None:
    model = ClientUpdate(id=uuid4(), name="some name")
    assert model.description is None
    assert model.sources is None
    assert model.certificates is None


def test_update_only_tracks_supplied_fields() -> None:
    mock_id = uuid4()
    model = ClientUpdate(id=mock_id, name="New Name")
    assert model.model_dump(exclude_unset=True) == {"id": mock_id, "name": "New Name"}


def test_query_params_all_optional_and_track_supplied_only() -> None:
    assert ClientQueryParams().model_dump(exclude_unset=True) == {}
    params = ClientQueryParams(name="some name", scopes=[AuthorizationScope("nvi:read")])
    assert params.model_dump(exclude_unset=True) == {"name": "some name", "scopes": ["nvi:read"]}


def test_resolve_request_should_succeed() -> None:
    org_ura = UraNumber("12345678")
    mock_client_id = uuid4()
    model = ClientResolveRequest(
        client_id=mock_client_id,
        organization_external_id=TEST_EXTERNAL_ID,
        certificate_organization_identifier=TEST_OIN,
        certificate_domains=[TEST_DOMAIN],
    )
    assert str(model.client_id) == str(mock_client_id)
    assert str(model.certificate_organization_identifier) == str(TEST_OIN)
    assert str(model.organization_external_id) == str(org_ura)
    assert model.certificate_domains == [TEST_DOMAIN]
    assert model.source_id is None


def test_resolve_request_missing_org_id_should_raise() -> None:
    with pytest.raises(ValidationError):
        ClientResolveRequest(  # type: ignore[call-arg]
            client_organization_id=TEST_OIN,
            client_common_name="Test Client",
        )


def test_resolve_response_requires_scopes_and_matched_domain() -> None:
    with pytest.raises(ValidationError):
        ClientResolveResponse(organization_name=TEST_ORG_NAME)  # type: ignore[call-arg]

    model = ClientResolveResponse(scopes="nvi:localize", organization_name=TEST_ORG_NAME, matched_domain=TEST_DOMAIN)
    assert model.matched_domain == TEST_DOMAIN
    assert model.scopes == "nvi:localize"
