from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import InvalidRequestError

from app.db.models.certificate import CertificateEntity
from app.db.models.client import ClientEntity
from app.db.models.organization import OrganizationEntity
from app.db.models.source import SourceEntity
from app.db.repository.organization import OrganizationRepository
from app.db.repository.query_builder.context.organization_context import (
    OrganizationCertificateQueryContext,
    OrganizationClientQueryContext,
    OrganizationQueryContext,
    OrganizationSourceQueryContext,
)
from app.db.repository.query_builder.data import LoadStrategy
from app.models.oin import Oin
from app.models.ura import UraNumber
from tests.conftest import TEST_EXTERNAL_ID


def test_add_one(
    organization_repository: OrganizationRepository,
    organization_entity: OrganizationEntity,
) -> None:
    with organization_repository.db_session:
        result = organization_repository.add_one(organization_entity)
        assert result == organization_entity


def test_find_one_found(
    organization_repository: OrganizationRepository,
    organization_entity: OrganizationEntity,
) -> None:
    with organization_repository.db_session:
        organization_repository.add_one(organization_entity)
        result = organization_repository.find_one(organization_entity.id)
        assert result is not None
        assert result.id == organization_entity.id


def test_find_one_not_found(organization_repository: OrganizationRepository) -> None:
    with organization_repository.db_session:
        expected = organization_repository.find_one(uuid4())
        assert expected is None


def test_exists_found(
    organization_repository: OrganizationRepository,
    organization_entity: OrganizationEntity,
) -> None:
    with organization_repository.db_session:
        organization_repository.add_one(organization_entity)
        expected = organization_repository.exists(organization_entity.id)
        assert expected is True


def test_exists_not_found(organization_repository: OrganizationRepository) -> None:
    with organization_repository.db_session:
        expected = organization_repository.exists(uuid4())
        assert expected is False


def test_find_should_return_by_register_id(
    organization_repository: OrganizationRepository,
    organization_entity: OrganizationEntity,
) -> None:
    with organization_repository.db_session:
        organization_repository.add_one(organization_entity)
        ctx = OrganizationQueryContext(external_id=TEST_EXTERNAL_ID)
        result = organization_repository.find(ctx)
        assert result is not None
        assert result.external_id == TEST_EXTERNAL_ID


def test_find_should_raise_when_accessing_clients_and_not_called_in_context(
    organization_repository: OrganizationRepository,
    organization_entity: OrganizationEntity,
) -> None:
    with organization_repository.db_session:
        org = organization_repository.add_one(organization_entity)
        ctx = OrganizationQueryContext(id=org.id)

    # another session is required to simulate the call and avoid sqlachemy cache identitfy map
    # this can also be simulated with `session.flush()` and `session.expire_all()`
    # other tests addressing this issue will use the later for simplicity purposes.
    with organization_repository.db_session:
        result = organization_repository.find(ctx)
        assert result is not None
        with pytest.raises(InvalidRequestError):
            _ = result.clients


def test_find_should_raise_when_accessing_certificates_and_not_called_in_context(
    organization_repository: OrganizationRepository,
    organization_entity: OrganizationEntity,
) -> None:
    with organization_repository.db_session as session:
        org = organization_repository.add_one(organization_entity)
        ctx = OrganizationQueryContext(id=org.id)
        session.session.flush()
        session.session.expire_all()

        result = organization_repository.find(ctx)
        assert result is not None
        with pytest.raises(InvalidRequestError):
            _ = result.certificates


def test_find_should_raise_when_accessing_sources_and_not_called_in_context(
    organization_repository: OrganizationRepository,
    organization_entity: OrganizationEntity,
) -> None:
    with organization_repository.db_session as session:
        org = organization_repository.add_one(organization_entity)
        ctx = OrganizationQueryContext(id=org.id, client_ctx=None)
        session.session.flush()
        session.session.expire_all()

        result = organization_repository.find(ctx)
        assert result is not None
        with pytest.raises(InvalidRequestError):
            _ = result.sources


def test_find_should_only_return_what_is_called_in_context(
    organization_repository: OrganizationRepository,
    organization_entity: OrganizationEntity,
    client_entity: ClientEntity,
    certificate_entity: CertificateEntity,
) -> None:
    with organization_repository.db_session as session:
        organization_entity.clients.append(client_entity)
        organization_entity.certificates.append(certificate_entity)
        org = organization_repository.add_one(organization_entity)
        session.session.flush()
        session.session.expire_all()

        ctx = OrganizationQueryContext(id=org.id, client_ctx=OrganizationClientQueryContext())
        result = organization_repository.find(ctx)

        assert result is not None
        assert len(result.clients) > 0

        with pytest.raises(InvalidRequestError):
            _ = result.certificates


def test_find_should_give_proper_results_on_filtered_children(
    organization_repository: OrganizationRepository,
    organization_entity: OrganizationEntity,
    client_entity: ClientEntity,
    certificate_entity: CertificateEntity,
    source_entity: SourceEntity,
) -> None:
    with organization_repository.db_session as session:
        organization_entity.clients.append(client_entity)
        organization_entity.clients.append(ClientEntity(name="Other Test Client"))
        organization_entity.certificates.append(certificate_entity)
        organization_entity.certificates.append(
            CertificateEntity(organization_identifier=Oin("00000099000000002000"), domain="some-other-domain")
        )
        organization_entity.sources.append(source_entity)
        organization_entity.sources.append(SourceEntity(source_id="source-id-2", name="some-other-source"))
        org = organization_repository.add_one(organization_entity)
        certificate_entity_2 = org.certificates[1]
        client_entity_2 = org.clients[1]
        source_entity_2 = org.sources[1]
        session.session.flush()
        session.session.expire_all()

        ctx = OrganizationQueryContext(
            id=org.id,
            client_ctx=OrganizationClientQueryContext(organization_id=org.id, name=client_entity.name),
            certificate_ctx=OrganizationCertificateQueryContext(
                organization_identifier=certificate_entity.organization_identifier, domain=certificate_entity.domain
            ),
            source_ctx=OrganizationSourceQueryContext(source_id=source_entity.source_id),
        )
        result = organization_repository.find(ctx)

        assert result is not None
        assert result.id == org.id

        expected_cert = result.certificates[0]
        assert len(result.certificates) == 1
        assert certificate_entity_2.unique_key not in [c.unique_key for c in result.certificates]
        assert expected_cert.organization_id == org.id
        assert expected_cert.organization_identifier == certificate_entity.organization_identifier
        assert expected_cert.domain == certificate_entity.domain

        expected_client = result.clients[0]
        assert len(result.clients) == 1
        assert client_entity_2.id not in [c.id for c in result.clients]
        assert expected_client.organization_id == org.id
        assert expected_client.name == client_entity.name
        assert expected_client.description == client_entity.description

        expected_source = result.sources[0]
        assert source_entity_2.source_id not in [s.source_id for s in result.sources]
        assert expected_source == source_entity


def test_find_should_return_root_org_and_empty_children(
    organization_repository: OrganizationRepository,
    organization_entity: OrganizationEntity,
    client_entity: ClientEntity,
) -> None:
    with organization_repository.db_session as session:
        organization_entity.clients.append(client_entity)
        org = organization_repository.add_one(organization_entity)
        session.session.flush()
        session.session.expire_all()

        ctx = OrganizationQueryContext(
            external_id=organization_entity.external_id,
            client_ctx=OrganizationClientQueryContext(id=uuid4(), organization_id=org.id),
        )
        result = organization_repository.find(ctx)

        assert result is not None
        assert result.id == org.id
        assert len(result.clients) == 0


def test_find_should_include_deleted(
    organization_repository: OrganizationRepository,
    organization_entity: OrganizationEntity,
) -> None:
    organization_entity.deleted_at = datetime.now()
    with organization_repository.db_session:
        organization_repository.add_one(organization_entity)

        ctx = OrganizationQueryContext(external_id=TEST_EXTERNAL_ID)
        result = organization_repository.find(ctx, include_delete=True)

        assert result is not None


def test_find_many_returns_all(
    organization_repository: OrganizationRepository,
    organization_entity: OrganizationEntity,
) -> None:
    entity_2 = OrganizationEntity(external_id="87654321", name="Another Organization")
    with organization_repository.db_session:
        organization_repository.add_one(organization_entity)
        organization_repository.add_one(entity_2)
        ctx = OrganizationQueryContext()
        assert len(organization_repository.find_many(ctx)) == 2


def test_find_many_filters_by_register_id(
    organization_repository: OrganizationRepository,
    organization_entity: OrganizationEntity,
) -> None:
    entity_2 = OrganizationEntity(external_id="87654321", name="Another Organization")
    with organization_repository.db_session:
        organization_repository.add_one(organization_entity)
        organization_repository.add_one(entity_2)
        ctx = OrganizationQueryContext(external_id=TEST_EXTERNAL_ID)
        results = organization_repository.find_many(ctx)
        assert len(results) == 1
        assert results[0].id == organization_entity.id


def test_find_many_should_filter_on_children(
    organization_repository: OrganizationRepository,
    organization_entity: OrganizationEntity,
    certificate_entity: CertificateEntity,
    client_entity: ClientEntity,
    source_entity: SourceEntity,
) -> None:
    with organization_repository.db_session as session:
        organization_entity.clients.append(client_entity)
        organization_entity.clients.append(ClientEntity(name="Other Test Client"))
        organization_entity.certificates.append(certificate_entity)
        organization_entity.certificates.append(
            CertificateEntity(organization_identifier=Oin("00000099000000002000"), domain="some-other-domain")
        )
        organization_repository.add_one(
            OrganizationEntity(external_id=UraNumber("90002001"), name="some-other-org-name")
        )
        organization_entity.sources.append(source_entity)
        organization_entity.sources.append(SourceEntity(source_id="source-id-2", name="some-other-source"))

        org = organization_repository.add_one(organization_entity)
        certificate_entity_2 = org.certificates[1]
        client_entity_2 = org.clients[1]
        source_entity_2 = org.sources[1]
        session.session.flush()
        session.session.expire_all()

        ctx = OrganizationQueryContext(
            external_id=org.external_id,
            client_ctx=OrganizationClientQueryContext(organization_id=org.id, name=client_entity.name),
            certificate_ctx=OrganizationCertificateQueryContext(
                organization_identifier=certificate_entity.organization_identifier, domain=certificate_entity.domain
            ),
            source_ctx=OrganizationSourceQueryContext(source_id=source_entity.source_id),
        )
        results = organization_repository.find_many(ctx)
        actual_org = results[0]
        actual_clients = actual_org.clients
        actual_certificates = actual_org.certificates
        actual_sources = actual_org.sources

        assert len(results) == 1
        assert certificate_entity_2.unique_key not in [c.unique_key for c in actual_org.certificates]
        assert client_entity_2.id not in [c.id for c in actual_org.clients]
        assert source_entity_2.source_id not in [s.source_id for s in actual_org.sources]

        assert len(actual_clients) == 1
        assert actual_clients[0] == client_entity

        assert len(actual_certificates) == 1
        assert actual_certificates[0] == certificate_entity

        assert len(actual_sources) == 1
        assert actual_sources[0] == source_entity


def test_find_many_excludes_deleted(
    organization_repository: OrganizationRepository,
    organization_entity: OrganizationEntity,
) -> None:
    with organization_repository.db_session:
        organization_entity.deleted_at = datetime.now()
        organization_repository.add_one(organization_entity)
        ctx = OrganizationQueryContext()
        assert organization_repository.find_many(ctx) == []


def test_find_many_include_deleted_returns_deleted(
    organization_repository: OrganizationRepository,
    organization_entity: OrganizationEntity,
) -> None:
    with organization_repository.db_session:
        organization_entity.deleted_at = datetime.now()
        organization_repository.add_one(organization_entity)
        ctx = OrganizationQueryContext()
        results = organization_repository.find_many(ctx=ctx, include_deleted=True)
        assert len(results) == 1
        assert results[0].id == organization_entity.id


@pytest.mark.parametrize(
    "ctx",
    [
        OrganizationQueryContext(external_id=UraNumber("90001001"), name="Example Name"),
        OrganizationQueryContext(
            source_ctx=OrganizationSourceQueryContext(id=None, source_id=None, name=None),
            certificate_ctx=OrganizationCertificateQueryContext(id=None, organization_identifier=None, domain=None),
            client_ctx=None,
        ),
        OrganizationQueryContext(
            client_ctx=OrganizationClientQueryContext(
                name=None, description=None, source_ctx=None, certificate_ctx=None
            )
        ),
        OrganizationQueryContext(
            external_id=UraNumber("90001001"),
            name="Example Name",
            certificate_ctx=OrganizationCertificateQueryContext(organization_identifier=None, domain=None),
        ),
    ],
)
def test_determine_strategy_should_return_selectin_when_root_attr_values_only_exists(
    organization_repository: OrganizationRepository,
    ctx: OrganizationQueryContext,
) -> None:
    actual = organization_repository._determine_strategy(ctx)
    assert actual == LoadStrategy.SELECTIN_LOAD


@pytest.mark.parametrize(
    "ctx",
    [
        OrganizationQueryContext(
            source_ctx=OrganizationSourceQueryContext(source_id="source-1"),
            certificate_ctx=OrganizationCertificateQueryContext(domain="example-domain"),
        ),
        OrganizationQueryContext(
            client_ctx=OrganizationClientQueryContext(
                name="client-name",
            )
        ),
        OrganizationQueryContext(
            client_ctx=OrganizationClientQueryContext(source_ctx=OrganizationSourceQueryContext(source_id="some-id"))
        ),
        OrganizationQueryContext(
            client_ctx=OrganizationClientQueryContext(
                certificate_ctx=OrganizationCertificateQueryContext(
                    domain="some-domain", organization_identifier=Oin("00000099000000002000")
                )
            )
        ),
        OrganizationQueryContext(
            certificate_ctx=OrganizationCertificateQueryContext(
                domain="some-domain", organization_identifier=Oin("00000099000000002000")
            ),
        ),
    ],
)
def test_determine_strategy_should_return_joinload_when_children_attr_values_present(
    organization_repository: OrganizationRepository,
    ctx: OrganizationQueryContext,
) -> None:
    actual = organization_repository._determine_strategy(ctx)
    assert actual == LoadStrategy.OUTERJOIN_LOAD
