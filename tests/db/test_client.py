from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import InvalidRequestError

from app.db.models.certificate import CertificateEntity
from app.db.models.client import ClientEntity
from app.db.models.organization import OrganizationEntity
from app.db.models.source import SourceEntity
from app.db.repository.client import ClientRepository
from app.db.repository.organization import OrganizationRepository
from app.db.repository.query_builder.context.client_context import (
    ClientCertificateQueryContext,
    ClientQueryContext,
    ClientSourceQueryContext,
)
from app.db.repository.query_builder.data import LoadStrategy
from app.models.oin import Oin
from app.models.ura import UraNumber
from tests.conftest import TEST_DOMAIN, TEST_EXTERNAL_ID, TEST_OIN, TEST_ORG_NAME


def test_find_one(
    client_repository: ClientRepository, client_entity: ClientEntity, organization_entity: OrganizationEntity
) -> None:
    with client_repository.db_session:
        client_entity.organization = organization_entity
        result = client_repository.add_one(client_entity)
        assert result == client_entity


def test_find_one_found(
    client_repository: ClientRepository,
    organization_repository: OrganizationRepository,
    client_entity: ClientEntity,
    organization_entity: OrganizationEntity,
) -> None:
    with client_repository.db_session:
        client_entity.organization = organization_entity
        client = client_repository.add_one(client_entity)
        result = client_repository.find_one(client.id, client.organization_id)
        assert result is not None
        assert result.id == client_entity.id


def test_find_one_not_found(
    client_repository: ClientRepository,
    client_entity: ClientEntity,
    organization_entity: OrganizationEntity,
) -> None:
    with client_repository.db_session:
        client_entity.organization = organization_entity
        client = client_repository.add_one(client_entity)
        actual = client_repository.find_one(uuid4(), client.organization_id)
        assert actual is None


def test_find_one_wrong_organization(
    client_repository: ClientRepository,
    client_entity: ClientEntity,
    organization_entity: OrganizationEntity,
) -> None:
    with client_repository.db_session:
        client_entity.organization = organization_entity
        client = client_repository.add_one(client_entity)
        assert client_repository.find_one(client.id, uuid4()) is None


def test_find_many_returns_all(
    client_repository: ClientRepository,
    organization_repository: OrganizationRepository,
    client_entity: ClientEntity,
    organization_entity: OrganizationEntity,
) -> None:
    client_entity_2 = ClientEntity(organization_id=client_entity.organization_id, name="Test Client 2")
    with organization_repository.db_session:
        organization_entity.clients.extend([client_entity, client_entity_2])
        org = organization_repository.add_one(organization_entity)

    with client_repository.db_session:
        ctx = ClientQueryContext(organization_id=org.id)
        results = client_repository.find_many(ctx)
        assert len(results) == 2


def test_find_many_should_filter_on_client_attr(
    client_repository: ClientRepository,
    organization_repository: OrganizationRepository,
    client_entity: ClientEntity,
    organization_entity: OrganizationEntity,
    certificate_entity: CertificateEntity,
    source_entity: SourceEntity,
) -> None:
    client_entity_2 = ClientEntity(organization_id=client_entity.organization_id, name="Test Client 2")
    with organization_repository.db_session:
        organization_entity.certificates.append(certificate_entity)
        organization_entity.sources.append(source_entity)
        client_entity.certificates.append(certificate_entity)
        client_entity.sources.append(source_entity)
        organization_entity.clients.extend([client_entity, client_entity_2])
        org = organization_repository.add_one(organization_entity)

    with client_repository.db_session:
        ctx = ClientQueryContext(name=client_entity.name, organization_id=org.id)
        actual = client_repository.find_many(ctx)

        assert len(actual) == 1


def test_find_many_should_filter_on_children_attr(
    client_repository: ClientRepository,
    organization_repository: OrganizationRepository,
    client_entity: ClientEntity,
    organization_entity: OrganizationEntity,
    certificate_entity: CertificateEntity,
    source_entity: SourceEntity,
) -> None:
    client_entity_2 = ClientEntity(organization_id=client_entity.organization_id, name="Test Client 2")
    with organization_repository.db_session:
        organization_entity.certificates.append(certificate_entity)
        organization_entity.sources.append(source_entity)
        client_entity.certificates.append(certificate_entity)
        client_entity.sources.append(source_entity)
        organization_entity.clients.extend([client_entity, client_entity_2])
        org = organization_repository.add_one(organization_entity)

    with client_repository.db_session:
        ctx = ClientQueryContext(
            organization_id=org.id,
            source_ctx=ClientSourceQueryContext(source_id=source_entity.source_id),
            certificate_ctx=ClientCertificateQueryContext(
                organization_identifier=certificate_entity.organization_identifier, domain=certificate_entity.domain
            ),
        )
        actual = client_repository.find_many(ctx)

        assert len(actual) == 1
        assert actual[0].id == org.clients[0].id


def test_find_many_excludes_deleted(
    client_repository: ClientRepository,
    organization_repository: OrganizationRepository,
    client_entity: ClientEntity,
    organization_entity: OrganizationEntity,
) -> None:

    client_entity_2 = ClientEntity(
        organization_id=client_entity.organization_id, name="Test Client 2", deleted_at=datetime.now()
    )
    with organization_repository.db_session:
        client_entity.deleted_at = datetime.now()
        organization_entity.clients.extend([client_entity, client_entity_2])
        org = organization_repository.add_one(organization_entity)

    with client_repository.db_session:
        ctx = ClientQueryContext(organization_id=org.id)
        actual = client_repository.find_many(ctx)

        assert len(actual) == 0


def test_find_many_include_deleted_returns_deleted(
    client_repository: ClientRepository,
    organization_repository: OrganizationRepository,
    client_entity: ClientEntity,
    organization_entity: OrganizationEntity,
) -> None:
    client_entity_2 = ClientEntity(
        organization_id=client_entity.organization_id, name="Test Client 2", deleted_at=datetime.now()
    )
    with organization_repository.db_session:
        client_entity.deleted_at = datetime.now()
        organization_entity.clients.extend([client_entity, client_entity_2])
        org = organization_repository.add_one(organization_entity)

    with client_repository.db_session:
        ctx = ClientQueryContext(organization_id=org.id)
        actual = client_repository.find_many(ctx, include_deleted=True)

        assert len(actual) == 2


def test_find_many_scoped_to_organization(
    client_repository: ClientRepository,
    organization_repository: OrganizationRepository,
    client_entity: ClientEntity,
    organization_entity: OrganizationEntity,
) -> None:
    with organization_repository.db_session:
        organization_entity.clients.append(client_entity)
        organization_repository.add_one(organization_entity)

    with client_repository.db_session:
        client_repository.add_one(client_entity)
        ctx = ClientQueryContext(id=uuid4())
        assert client_repository.find_many(ctx) == []


def test_find_many_should_raise_when_child_context_is_not_declared(
    client_repository: ClientRepository,
    organization_repository: OrganizationRepository,
    client_entity: ClientEntity,
    organization_entity: OrganizationEntity,
    certificate_entity: CertificateEntity,
    source_entity: SourceEntity,
) -> None:
    with organization_repository.db_session:
        organization_entity.certificates.append(certificate_entity)
        organization_entity.sources.append(source_entity)
        client_entity.certificates.append(certificate_entity)
        client_entity.sources.append(source_entity)
        organization_entity.clients.append(client_entity)
        org = organization_repository.add_one(organization_entity)

    with client_repository.db_session:
        ctx = ClientQueryContext(
            organization_id=org.id,
            certificate_ctx=ClientCertificateQueryContext(
                organization_identifier=certificate_entity.organization_identifier, domain=certificate_entity.domain
            ),
        )
        actuals = client_repository.find_many(ctx)
        assert len(actuals) == 1

        client = actuals[0]
        actual_cert = client.certificates[0]
        assert actual_cert.organization_identifier == certificate_entity.organization_identifier
        assert actual_cert.domain == certificate_entity.domain
        assert actual_cert.organization_id == org.id

        with pytest.raises(InvalidRequestError):
            _ = client.sources


def test_find_should_succeed_on_filter_and_return_exact(
    client_repository: ClientRepository,
    organization_repository: OrganizationRepository,
    client_entity: ClientEntity,
    organization_entity: OrganizationEntity,
    certificate_entity: CertificateEntity,
    source_entity: SourceEntity,
) -> None:
    cert_entity_2 = CertificateEntity(organization_identifier=Oin("00000099000000002000"), domain="some-other-domain")

    source_2 = SourceEntity(source_id="source-2", name="another-source")
    with organization_repository.db_session:
        organization_entity.certificates.extend([certificate_entity, cert_entity_2])
        organization_entity.sources.extend([source_entity, source_2])
        client_entity.certificates.extend([certificate_entity, cert_entity_2])
        client_entity.sources.extend([source_entity, source_2])
        organization_entity.clients.append(client_entity)
        org = organization_repository.add_one(organization_entity)

    with client_repository.db_session:
        ctx = ClientQueryContext(
            organization_id=org.id,
            certificate_ctx=ClientCertificateQueryContext(
                organization_identifier=certificate_entity.organization_identifier, domain=certificate_entity.domain
            ),
            source_ctx=ClientSourceQueryContext(source_id=source_entity.source_id),
        )

        actual = client_repository.find(ctx)

        assert actual is not None
        assert actual.organization_id == org.id
        assert actual.id == org.clients[0].id

        assert len(actual.certificates) == 1
        assert cert_entity_2.unique_key not in [c.unique_key for c in actual.certificates]
        cert = actual.certificates[0]
        assert cert.organization_identifier == certificate_entity.organization_identifier
        assert cert.domain == certificate_entity.domain

        assert len(actual.sources) == 1
        assert source_2.source_id not in [s.source_id for s in actual.sources]
        src = actual.sources[0]
        assert src.organization_id == org.id
        assert src.source_id == source_entity.source_id


def test_find_should_only_return_what_is_requested_in_context(
    client_repository: ClientRepository,
    organization_repository: OrganizationRepository,
    client_entity: ClientEntity,
    organization_entity: OrganizationEntity,
    certificate_entity: CertificateEntity,
    source_entity: SourceEntity,
) -> None:
    with organization_repository.db_session:
        organization_entity.certificates.append(certificate_entity)
        organization_entity.sources.append(source_entity)
        client_entity.certificates.append(certificate_entity)
        client_entity.sources.append(source_entity)
        organization_entity.clients.append(client_entity)
        org = organization_repository.add_one(organization_entity)

        with client_repository.db_session:
            ctx = ClientQueryContext(
                organization_id=org.id, source_ctx=ClientSourceQueryContext(source_id=source_entity.source_id)
            )
            actual = client_repository.find(ctx)

            assert actual is not None
            assert actual.organization_id == org.id
            assert actual.name == client_entity.name

            assert len(actual.sources) == 1
            actual_src = actual.sources[0]
            assert actual_src.organization_id == org.id
            assert actual_src.source_id == source_entity.source_id

            with pytest.raises(InvalidRequestError):
                _ = actual.certificates


@pytest.mark.parametrize(
    "ctx",
    [
        ClientQueryContext(
            id=uuid4(),
            organization_id=uuid4(),
            name="Test Client",
            description="Active Client",
            scopes=["read", "write"],
            certificate_ctx=None,
            source_ctx=None,
        ),
        ClientQueryContext(
            id=None,
            organization_id=None,
            name=None,
            description=None,
            scopes=None,
            certificate_ctx=ClientCertificateQueryContext(id=None, organization_identifier=None, domain=None),
            source_ctx=ClientSourceQueryContext(id=None, source_id=None, name=None),
        ),
    ],
)
def test_determine_strategy_should_return_selectin_when_root_attr_values_only_exists_for_client(
    client_repository: ClientRepository,
    ctx: ClientQueryContext,
) -> None:
    actual = client_repository._determine_strategy(ctx)
    assert actual == LoadStrategy.SELECTIN_LOAD


@pytest.mark.parametrize(
    "ctx",
    [
        # Case 1: Certificate child sub-context filter active (id)
        ClientQueryContext(certificate_ctx=ClientCertificateQueryContext(domain="some-domain")),
        # Case 2: Certificate child sub-context filter active (domain)
        ClientQueryContext(
            certificate_ctx=ClientCertificateQueryContext(organization_identifier=Oin("00000099000000002000"))
        ),
        # Case 3: Source child sub-context filter active (source_id)
        ClientQueryContext(source_ctx=ClientSourceQueryContext(source_id="source-1")),
        # Case 4: Source child sub-context filter active (name)
        ClientQueryContext(source_ctx=ClientSourceQueryContext(name="some-source")),
    ],
)
def test_determine_strategy_should_return_outerjoin_when_child_filters_exist_for_client(
    client_repository: ClientRepository,
    ctx: ClientQueryContext,
) -> None:
    actual = client_repository._determine_strategy(ctx)
    assert actual == LoadStrategy.OUTERJOIN_LOAD


def test_accessing_organization_raises_lazy_load(
    client_repository: ClientRepository, client_entity: ClientEntity, organization_entity: OrganizationEntity
) -> None:
    with client_repository.db_session as session:
        client_entity.organization = organization_entity
        client = client_repository.add_one(client_entity)
        session.session.flush()
        session.session.expire_all()

        result = client_repository.find_one(client.id, client.organization_id)
        assert result is not None
        with pytest.raises(InvalidRequestError):
            _ = result.organization


def test_get_by_credentials_matches_via_organization_register_id(
    client_repository: ClientRepository,
    client_entity: ClientEntity,
) -> None:
    with client_repository.db_session:
        client_repository.add_one(client_entity)
        result = client_repository.get_by_credentials(common_name=TEST_DOMAIN, oin=TEST_OIN, org_ura=TEST_EXTERNAL_ID)
        assert result is not None
        assert result.id == client_entity.id
        assert result.organization.name == TEST_ORG_NAME


def test_get_by_credentials_unknown_org_ura_returns_none(
    client_repository: ClientRepository,
    client_entity: ClientEntity,
) -> None:
    with client_repository.db_session:
        client_repository.add_one(client_entity)
        result = client_repository.get_by_credentials(
            common_name=TEST_DOMAIN, oin=TEST_OIN, org_ura=UraNumber("99999999")
        )
        assert result is None
