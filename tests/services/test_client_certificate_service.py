from uuid import uuid4

import pytest

from app.models.certificates import CertificateCreate, ClientCertificateQueryParams
from app.models.organization import OrganizationCreate
from app.services.certificate.client_certificate import ClientCertificateService
from app.services.client import ClientService
from app.services.exceptions import ConflictError, RecordNotFoundError
from app.services.organization import OrganizationService
from tests.conftest import SECOND_DOMAIN, SECOND_OIN, TEST_DOMAIN, TEST_OIN


def test_get_one_should_succeed(
    organization_service: OrganizationService,
    client_certificate_service: ClientCertificateService,
    org_create_dto_1: OrganizationCreate,
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    assert org.clients is not None
    client = org.clients[0]
    assert client.certificates is not None
    expected = client.certificates[0]

    actual = client_certificate_service.get_one(org.id, client.id, expected.id)

    assert expected == actual


def test_get_one_should_raise_on_wrong_combination(
    organization_service: OrganizationService,
    client_certificate_service: ClientCertificateService,
    org_create_dto_1: OrganizationCreate,
    org_create_dto_2: OrganizationCreate,
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    org_2 = organization_service.create_one(org_create_dto_2)
    assert org.clients is not None
    client = org.clients[0]
    assert client.certificates is not None
    cert = client.certificates[0]

    with pytest.raises(RecordNotFoundError):
        _ = client_certificate_service.get_one(org_2.id, client.id, cert.id)


def test_get_one_should_raise_on_unknown_cert_id(
    organization_service: OrganizationService,
    client_certificate_service: ClientCertificateService,
    org_create_dto_1: OrganizationCreate,
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    assert org.clients is not None
    client = org.clients[0]
    assert client.certificates is not None

    with pytest.raises(RecordNotFoundError):
        _ = client_certificate_service.get_one(org.id, client.id, uuid4())


def test_get_many_should_succeed(
    organization_service: OrganizationService,
    client_certificate_service: ClientCertificateService,
    org_create_dto_1: OrganizationCreate,
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    assert org.clients is not None
    client = org.clients[0]
    assert client.certificates is not None
    expected = client.certificates

    actual = client_certificate_service.get_many(org.id, client.id, ClientCertificateQueryParams())

    assert len(expected) == len(actual)
    assert expected == actual


@pytest.mark.parametrize(
    "params",
    [
        ClientCertificateQueryParams(organization_identifier=TEST_OIN),
        ClientCertificateQueryParams(domain=TEST_DOMAIN),
        ClientCertificateQueryParams(organization_identifier=TEST_OIN, domain=TEST_DOMAIN),
    ],
)
def test_get_many_should_filter_on_params(
    organization_service: OrganizationService,
    client_certificate_service: ClientCertificateService,
    org_create_dto_1: OrganizationCreate,
    cert_create_dto_2: CertificateCreate,
    params: ClientCertificateQueryParams,
) -> None:
    org_create_dto_1.clients[0].certificates.append(cert_create_dto_2)  # type: ignore
    org = organization_service.create_one(org_create_dto_1)
    assert org.clients is not None
    client = org.clients[0]
    assert client.certificates is not None
    expected = client.certificates[0]
    cert_not_in_result = client.certificates[1]

    actual = client_certificate_service.get_many(org.id, client.id, params)

    assert [expected] == actual
    assert cert_not_in_result.id not in [c.id for c in actual]


@pytest.mark.parametrize(
    "params",
    [
        ClientCertificateQueryParams(organization_identifier=SECOND_OIN),
        ClientCertificateQueryParams(domain=SECOND_DOMAIN),
        ClientCertificateQueryParams(organization_identifier=SECOND_OIN, domain=SECOND_DOMAIN),
    ],
)
def test_get_many_should_return_empty_list_on_no_match(
    organization_service: OrganizationService,
    client_certificate_service: ClientCertificateService,
    org_create_dto_1: OrganizationCreate,
    params: ClientCertificateQueryParams,
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    assert org.clients is not None
    client = org.clients[0]
    assert client.certificates is not None

    actual = client_certificate_service.get_many(org.id, client.id, params)

    assert actual == []


def test_get_many_should_raise_on_wrong_combination(
    organization_service: OrganizationService,
    client_certificate_service: ClientCertificateService,
    org_create_dto_1: OrganizationCreate,
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    assert org.clients is not None
    client = org.clients[0]
    assert client.certificates is not None

    with pytest.raises(RecordNotFoundError):
        _ = client_certificate_service.get_many(org.id, uuid4(), ClientCertificateQueryParams())

    with pytest.raises(RecordNotFoundError):
        _ = client_certificate_service.get_many(uuid4(), client.id, ClientCertificateQueryParams())


def test_assign_one_should_succeed(
    organization_service: OrganizationService,
    client_certificate_service: ClientCertificateService,
    client_service: ClientService,
    org_create_dto_1: OrganizationCreate,
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    assert org.clients is not None
    assert org.certificates is not None
    target_certs = org.certificates[1]
    client = org.clients[0]

    expected = client_certificate_service.assign_one(org.id, client.id, target_certs.id)
    updated_client = client_service.get_one(client.id, org.id)

    assert client.certificates is not None
    assert len(client.certificates) == 1
    assert expected.id not in [c.id for c in client.certificates]
    assert updated_client.certificates is not None
    assert len(updated_client.certificates) == 2
    assert expected.id in [c.id for c in updated_client.certificates]


def test_assign_one_should_fail_on_missmatch_params(
    organization_service: OrganizationService,
    client_certificate_service: ClientCertificateService,
    org_create_dto_1: OrganizationCreate,
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    assert org.clients is not None
    assert org.certificates is not None
    target_certs = org.certificates[1]
    client = org.clients[0]

    with pytest.raises(RecordNotFoundError):
        _ = client_certificate_service.assign_one(uuid4(), client.id, target_certs.id)

    with pytest.raises(RecordNotFoundError):
        _ = client_certificate_service.assign_one(org.id, uuid4(), target_certs.id)

    with pytest.raises(RecordNotFoundError):
        _ = client_certificate_service.assign_one(org.id, client.id, uuid4())


def test_assign_one_should_raise_on_duplicate_assignement(
    organization_service: OrganizationService,
    client_certificate_service: ClientCertificateService,
    org_create_dto_1: OrganizationCreate,
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    assert org.clients is not None
    assert org.certificates is not None
    target_certs = org.certificates[1]
    client = org.clients[0]

    _ = client_certificate_service.assign_one(org.id, client.id, target_certs.id)

    with pytest.raises(ConflictError):
        _ = client_certificate_service.assign_one(org.id, client.id, target_certs.id)


def test_unassing_one_should_succeed(
    organization_service: OrganizationService,
    client_certificate_service: ClientCertificateService,
    client_service: ClientService,
    org_create_dto_1: OrganizationCreate,
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    assert org.clients is not None
    assert org.certificates is not None
    target_certs = org.certificates[1]
    client = org.clients[0]

    _ = client_certificate_service.assign_one(org.id, client.id, target_certs.id)
    client_with_2_certs = client_service.get_one(client.id, org.id)
    _ = client_certificate_service.unassign_one(org.id, client.id, target_certs.id)
    updated_cient = client_service.get_one(client.id, org.id)

    assert client_with_2_certs.id == updated_cient.id
    assert client_with_2_certs.certificates is not None
    assert len(client_with_2_certs.certificates) == 2
    assert updated_cient.certificates is not None
    assert len(updated_cient.certificates) == 1


def test_unassign_one_should_raise_one_params_mismatch(
    organization_service: OrganizationService,
    client_certificate_service: ClientCertificateService,
    client_service: ClientService,
    org_create_dto_1: OrganizationCreate,
) -> None:
    org = organization_service.create_one(org_create_dto_1)
    assert org.clients is not None
    assert org.certificates is not None
    target_certs = org.certificates[1]
    client = org.clients[0]

    with pytest.raises(RecordNotFoundError):
        _ = client_certificate_service.unassign_one(org.id, client.id, uuid4())

    with pytest.raises(RecordNotFoundError):
        _ = client_certificate_service.unassign_one(org.id, uuid4(), target_certs.id)

    with pytest.raises(RecordNotFoundError):
        _ = client_certificate_service.unassign_one(uuid4(), client.id, target_certs.id)
