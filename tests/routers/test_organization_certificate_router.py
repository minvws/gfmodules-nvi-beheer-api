import pytest
from fastapi.testclient import TestClient

from app.db.repository.certificate import CertificateRepository
from app.models.certificates import Certificate, CertificateCreate
from app.models.organization import Organization, OrganizationCreate
from app.services.organization import OrganizationService
from tests.conftest import SECOND_OIN, TEST_DOMAIN


@pytest.fixture
def org(
    organization_service: OrganizationService,
    org_create_dto_1: OrganizationCreate,
    cert_create_dto_1: CertificateCreate,
) -> Organization:
    org_create_dto_1.clients = None
    org_create_dto_1.certificates = [
        cert_create_dto_1,
        CertificateCreate(organization_identifier=SECOND_OIN, domain=TEST_DOMAIN),
    ]
    return organization_service.create_one(org_create_dto_1)


def assert_update_conflicts(api: TestClient, org: Organization, target: Certificate, existing: Certificate) -> None:
    response = api.put(
        f"/organizations/{org.id}/certificate/{target.id}",
        json={
            "id": str(target.id),
            "organization_identifier": str(existing.organization_identifier),
            "domain": existing.domain,
        },
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": f"Certificate with organization_identifier: {existing.organization_identifier}, "
        f"domain: {existing.domain} already exists"
    }


def test_update_to_existing_identifier_and_domain_returns_409(api: TestClient, org: Organization) -> None:
    assert org.certificates is not None
    existing, target = org.certificates

    assert_update_conflicts(api, org, target, existing)


def test_update_to_existing_identifier_and_domain_caught_by_database_returns_409(
    api: TestClient, org: Organization, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert org.certificates is not None
    existing, target = org.certificates
    monkeypatch.setattr(CertificateRepository, "find_many", lambda *_args, **_kwargs: [])

    assert_update_conflicts(api, org, target, existing)


def test_update_domain_returns_200(api: TestClient, org: Organization) -> None:
    assert org.certificates is not None
    target = org.certificates[0]
    url = f"/organizations/{org.id}/certificate/{target.id}"

    response = api.put(
        url,
        json={
            "id": str(target.id),
            "organization_identifier": str(target.organization_identifier),
            "domain": "new.example",
        },
    )

    assert response.status_code == 200
    assert response.json()["domain"] == "new.example"
    assert api.get(url).json()["domain"] == "new.example"
