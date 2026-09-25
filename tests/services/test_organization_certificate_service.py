from uuid import uuid4

import pytest

from app.models.certificates import CertificateCreate, CertificateQueryParams
from app.models.organization import OrganizationCreate
from app.services.certificate.organization_certificate import OrganizationCertificateService
from app.services.exceptions import ConflictError, EntityHasActiveMemebersError, RecordNotFoundError
from app.services.organization import OrganizationService
from tests.conftest import SECOND_DOMAIN, SECOND_OIN, TEST_DOMAIN, TEST_OIN


def test_create_one_should_succeed(
    organization_certificate_service: OrganizationCertificateService,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
    cert_create_dto_1: CertificateCreate,
) -> None:
    org_create_dto_1.certificates = None
    org_create_dto_1.clients = None
    org = organization_service.create_one(org_create_dto_1)

    actual = organization_certificate_service.create_one(org.id, cert_create_dto_1)
    org_with_certs = organization_service.get_one(org.id)

    assert actual is not None
    assert org_with_certs is not None
    assert org_with_certs.certificates is not None
    assert org_with_certs.certificates[0] == actual


def test_create_one_should_raise_when_oin_and_domain_exists_on_same_org(
    organization_certificate_service: OrganizationCertificateService,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
    cert_create_dto_1: CertificateCreate,
) -> None:
    org = organization_service.create_one(org_create_dto_1)

    duplicate_cert = cert_create_dto_1.model_copy()

    with pytest.raises(ConflictError):
        organization_certificate_service.create_one(org.id, duplicate_cert)


def test_create_one_should_raise_when_org_not_found(
    organization_certificate_service: OrganizationCertificateService,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
    cert_create_dto_1: CertificateCreate,
) -> None:
    org_create_dto_1.certificates = None
    org_create_dto_1.clients = None
    _ = organization_service.create_one(org_create_dto_1)

    with pytest.raises(RecordNotFoundError):
        _ = organization_certificate_service.create_one(uuid4(), cert_create_dto_1)


def test_get_one_should_succeed(
    organization_certificate_service: OrganizationCertificateService,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
    cert_create_dto_1: CertificateCreate,
) -> None:
    org_create_dto_1.certificates = None
    org_create_dto_1.clients = None

    org = organization_service.create_one(org_create_dto_1)
    expected = organization_certificate_service.create_one(org.id, cert_create_dto_1)
    actual = organization_certificate_service.get_one(expected.id, org.id)

    assert expected == actual


def test_get_one_should_raise_on_wrong_org_and_cert_combination(
    organization_certificate_service: OrganizationCertificateService,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
    org_create_dto_2: OrganizationCreate,
    cert_create_dto_1: CertificateCreate,
) -> None:
    org_create_dto_1.clients = None
    org_create_dto_1.certificates = None
    org_create_dto_2.clients = None
    org_create_dto_2.certificates = None

    org_1 = organization_service.create_one(org_create_dto_1)
    org_2 = organization_service.create_one(org_create_dto_2)
    cert = organization_certificate_service.create_one(org_1.id, cert_create_dto_1)

    with pytest.raises(RecordNotFoundError):
        _ = organization_certificate_service.get_one(cert.id, org_2.id)


def test_get_one_should_fail_on_wront_org_id(
    organization_certificate_service: OrganizationCertificateService,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
    cert_create_dto_1: CertificateCreate,
) -> None:
    org_create_dto_1.clients = None
    org_create_dto_1.certificates = None

    org = organization_service.create_one(org_create_dto_1)
    cert = organization_certificate_service.create_one(org.id, cert_create_dto_1)

    with pytest.raises(RecordNotFoundError):
        _ = organization_certificate_service.get_one(cert.id, uuid4())


def test_get_many_should_succeed(
    organization_certificate_service: OrganizationCertificateService,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
) -> None:
    org = organization_service.create_one(org_create_dto_1)

    actual = organization_certificate_service.get_many(org.id, CertificateQueryParams())

    assert len(actual) == 2


@pytest.mark.parametrize(
    "params",
    [
        CertificateQueryParams(organization_identifier=TEST_OIN),
        CertificateQueryParams(domain=TEST_DOMAIN),
        CertificateQueryParams(organization_identifier=TEST_OIN, domain=TEST_DOMAIN),
    ],
)
def test_get_many_should_return_results_as_per_params(
    organization_certificate_service: OrganizationCertificateService,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
    params: CertificateQueryParams,
) -> None:
    org = organization_service.create_one(org_create_dto_1)

    actual = organization_certificate_service.get_many(org.id, params)

    assert org.certificates is not None
    assert len(org.certificates) == 2
    assert len(actual) == 1
    assert actual[0].organization_identifier == TEST_OIN
    assert actual[0].domain == TEST_DOMAIN


def test_get_many_should_return_on_deleted_flag(
    organization_certificate_service: OrganizationCertificateService,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
) -> None:
    org_create_dto_1.clients = None
    org = organization_service.create_one(org_create_dto_1)
    assert org.certificates is not None
    target = org.certificates[0]
    _ = organization_certificate_service.delete_one(org.id, target.id)

    actual = organization_certificate_service.get_many(org.id, CertificateQueryParams(include_deleted=False))

    assert len(org.certificates) == 2
    assert len(actual) == 1
    assert actual[0].organization_identifier == SECOND_OIN
    assert actual[0].domain == SECOND_DOMAIN
    assert actual[0].id == org.certificates[1].id


def test_delete_one_should_succeed(
    organization_certificate_service: OrganizationCertificateService,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
) -> None:
    org_create_dto_1.clients = None
    org = organization_service.create_one(org_create_dto_1)
    assert org.certificates is not None
    target = org.certificates[0]
    _ = organization_certificate_service.delete_one(org.id, target.id)

    with pytest.raises(RecordNotFoundError):
        _ = organization_certificate_service.delete_one(org.id, target.id)


def test_delete_one_should_raise_when_org_cert_combination_missmatch(
    organization_certificate_service: OrganizationCertificateService,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
    org_create_dto_2: OrganizationCreate,
) -> None:
    org_create_dto_1.clients = None
    org_create_dto_2.clients = None
    org_1 = organization_service.create_one(org_create_dto_1)
    org_2 = organization_service.create_one(org_create_dto_2)
    assert org_1.certificates is not None
    target = org_1.certificates[0]

    with pytest.raises(RecordNotFoundError):
        _ = organization_certificate_service.delete_one(org_2.id, target.id)


def test_delete_one_should_raise_when_cert_has_clients(
    organization_certificate_service: OrganizationCertificateService,
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
) -> None:
    org = organization_service.create_one(org_create_dto_1)

    assert org.certificates is not None
    assert org.clients is not None
    target = org.certificates[0]
    client = org.clients[0]
    assert client.certificates is not None
    assert target.id in [c.id for c in client.certificates]

    with pytest.raises(EntityHasActiveMemebersError):
        _ = organization_certificate_service.delete_one(org.id, target.id)
