from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import InvalidRequestError

from app.db.models.certificate import CertificateEntity
from app.db.models.client import ClientEntity
from app.db.models.organization import OrganizationEntity
from app.db.repository.certificate import CertificateRepository
from app.db.repository.contexts.certificate_context import (
    CertificateClientQueryContext,
    CertificateOrganizationQueryContext,
    CertificateQueryContext,
)
from app.db.repository.organization import OrganizationRepository
from app.models.oin import Oin
from app.models.ura import UraNumber


def test_find_one_should_succeed(
    organization_entity: OrganizationEntity,
    certificate_entity: CertificateEntity,
    certificate_repository: CertificateRepository,
    organization_repository: OrganizationRepository,
) -> None:
    with organization_repository.db_session:
        organization_entity.certificates.append(certificate_entity)
        org = organization_repository.add_one(organization_entity)
        cert = org.certificates[0]

    with certificate_repository.db_session:
        actual = certificate_repository.find_one(cert.id, org.id)

        assert actual is not None
        assert actual.id == cert.id
        assert actual.organization_id == cert.organization_id
        assert actual.organization_identifier == cert.organization_identifier
        assert actual.domain == cert.domain


def find_one_should_return_none_on_wrong_id(
    organization_entity: OrganizationEntity,
    certificate_entity: CertificateEntity,
    certificate_repository: CertificateRepository,
    organization_repository: OrganizationRepository,
) -> None:
    with organization_repository.db_session:
        organization_entity.certificates.append(certificate_entity)
        org = organization_repository.add_one(organization_entity)

    with certificate_repository.db_session:
        actual = certificate_repository.find_one(uuid4(), org.id)

        assert actual is None


def find_one_should_return_none_on_wrong_org_id(
    organization_entity: OrganizationEntity,
    certificate_entity: CertificateEntity,
    certificate_repository: CertificateRepository,
    organization_repository: OrganizationRepository,
) -> None:
    with organization_repository.db_session:
        organization_entity.certificates.append(certificate_entity)
        org = organization_repository.add_one(organization_entity)
        cert = org.certificates[0]

    with certificate_repository.db_session:
        actual = certificate_repository.find_one(cert.id, uuid4())

        assert actual is None


def test_find_many_should_return_all(
    organization_entity: OrganizationEntity,
    certificate_entity: CertificateEntity,
    certificate_repository: CertificateRepository,
    organization_repository: OrganizationRepository,
) -> None:
    cert_entity_2 = CertificateEntity(organization_identifier=Oin("00000099000000002000"), domain="some-other-domain")
    cert_entity_3 = CertificateEntity(organization_identifier=Oin("00000099000000002000"), domain="some-other-domain")
    org_entity_2 = OrganizationEntity(external_id=UraNumber("90001001"), name="Test Org 2")

    with organization_repository.db_session:
        organization_entity.certificates.extend([certificate_entity, cert_entity_2])
        organization_repository.add_one(organization_entity)

        org_entity_2.certificates.append(cert_entity_3)
        organization_repository.add_one(org_entity_2)

    with certificate_repository.db_session:
        ctx = CertificateQueryContext.default()
        results = certificate_repository.find_many(ctx)

        assert len(results) == 3


def test_find_many_should_filter_on_organization_identifier(
    organization_entity: OrganizationEntity,
    client_entity: ClientEntity,
    certificate_entity: CertificateEntity,
    organization_repository: OrganizationRepository,
    certificate_repository: CertificateRepository,
) -> None:
    cert_entity_2 = CertificateEntity(organization_identifier=Oin("00000099000000002000"), domain="some-other-domain")

    with organization_repository.db_session:
        organization_entity.certificates.extend([certificate_entity, cert_entity_2])
        organization_repository.add_one(organization_entity)

    with certificate_repository.db_session:
        ctx = CertificateQueryContext(
            organization_identifier=certificate_entity.organization_identifier, domain=certificate_entity.domain
        )

        results = certificate_repository.find_many(ctx)
        cert = results[0]

        assert len(results) == 1
        assert cert.id == certificate_entity.id
        assert cert.organization_identifier == certificate_entity.organization_identifier
        assert cert.domain == certificate_entity.domain
        assert cert.organization_id == organization_entity.id


def test_find_many_should_return_deleted_based_on_flag(
    organization_entity: OrganizationEntity,
    certificate_entity: CertificateEntity,
    certificate_repository: CertificateRepository,
    organization_repository: OrganizationRepository,
) -> None:
    cert_entity_2 = CertificateEntity(
        organization_identifier=Oin("00000099000000002000"), domain="some-other-domain", deleted_at=datetime.now()
    )
    with organization_repository.db_session:
        organization_entity.certificates.extend([certificate_entity, cert_entity_2])
        organization_repository.add_one(organization_entity)

    with certificate_repository.db_session as session:
        ctx = CertificateQueryContext.default()
        result = certificate_repository.find_many(ctx)
        assert len(result) == 1

        session.session.flush()
        session.session.expire_all()

        result = certificate_repository.find_many(ctx, include_deleted=True)
        assert len(result) == 2


def test_find_should_return_exact_match(
    organization_entity: OrganizationEntity,
    certificate_entity: CertificateEntity,
    client_entity: ClientEntity,
    certificate_repository: CertificateRepository,
    organization_repository: OrganizationRepository,
) -> None:
    cert_entity_2 = CertificateEntity(organization_identifier=Oin("00000099000000002000"), domain="some-other-domain")
    with organization_repository.db_session:
        organization_entity.certificates.extend([certificate_entity, cert_entity_2])
        client_entity.certificates.append(cert_entity_2)
        organization_entity.clients.append(client_entity)
        org = organization_repository.add_one(organization_entity)

    with certificate_repository.db_session as session:
        ctx = CertificateQueryContext(
            organization_identifier=certificate_entity.organization_identifier,
            domain=certificate_entity.domain,
            organization_id=org.id,
        )
        actual = certificate_repository.find(ctx)

        assert actual is not None
        assert actual.organization_identifier == certificate_entity.organization_identifier
        assert actual.domain == certificate_entity.domain
        assert actual.organization_id == org.id

        session.session.flush()
        session.session.expire_all()

        ctx = CertificateQueryContext(
            organization_identifier=cert_entity_2.organization_identifier,
            domain=cert_entity_2.domain,
            client_ctx=CertificateClientQueryContext(name=client_entity.name, organization_id=org.id),
        )

        actual = certificate_repository.find(ctx)

        assert actual is not None
        assert actual.organization_identifier == cert_entity_2.organization_identifier
        assert actual.domain == cert_entity_2.domain
        assert actual.organization_id == org.id
        assert len(actual.clients) == 1


def test_find_should_raise_on_load_for_attr_not_in_context(
    organization_entity: OrganizationEntity,
    certificate_entity: CertificateEntity,
    client_entity: ClientEntity,
    certificate_repository: CertificateRepository,
    organization_repository: OrganizationRepository,
) -> None:
    with organization_repository.db_session:
        organization_entity.certificates.append(certificate_entity)
        client_entity.certificates.append(certificate_entity)
        organization_entity.clients.append(client_entity)
        org = organization_repository.add_one(organization_entity)

    with certificate_repository.db_session as session:
        ctx = CertificateQueryContext(
            organization_identifier=certificate_entity.organization_identifier,
            domain=certificate_entity.domain,
            organization_ctx=CertificateOrganizationQueryContext(external_id=org.external_id),
        )
        actual = certificate_repository.find(ctx)

        assert actual is not None
        _ = actual.organization
        with pytest.raises(InvalidRequestError):
            _ = actual.clients

        session.session.flush()
        session.session.expire_all()

        ctx = CertificateQueryContext(
            organization_identifier=certificate_entity.organization_identifier,
            domain=certificate_entity.domain,
            client_ctx=CertificateClientQueryContext(name=client_entity.name, organization_id=org.id),
        )

        actual = certificate_repository.find(ctx)

        assert actual is not None
        assert len(actual.clients) == 1
        with pytest.raises(InvalidRequestError):
            _ = actual.organization


def test_find_should_return_none_when_no_match_found(
    organization_entity: OrganizationEntity,
    certificate_entity: CertificateEntity,
    organization_repository: OrganizationRepository,
    certificate_repository: CertificateRepository,
) -> None:
    with organization_repository.db_session:
        organization_entity.certificates.append(certificate_entity)
        org = organization_repository.add_one(organization_entity)

    with certificate_repository.db_session:
        ctx = CertificateQueryContext(id=uuid4(), organization_id=org.id)

        actual = certificate_repository.find(ctx)

        assert actual is None


def test_find_should_return_based_on_deleted_flag(
    organization_entity: OrganizationEntity,
    certificate_entity: CertificateEntity,
    organization_repository: OrganizationRepository,
    certificate_repository: CertificateRepository,
) -> None:
    certificate_entity.deleted_at = datetime.now()
    with organization_repository.db_session:
        organization_entity.certificates.append(certificate_entity)
        org = organization_repository.add_one(organization_entity)

    with certificate_repository.db_session as session:
        ctx = CertificateQueryContext(
            organization_identifier=certificate_entity.organization_identifier,
            domain=certificate_entity.domain,
            organization_id=org.id,
        )

        actual = certificate_repository.find(ctx)

        assert actual is None

        session.session.flush()
        session.session.expire_all()

        actual = certificate_repository.find(ctx, include_deleted=True)

        assert actual is not None
