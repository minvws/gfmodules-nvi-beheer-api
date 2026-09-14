from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import InvalidRequestError

from app.db.models.client import ClientEntity
from app.db.models.organization import OrganizationEntity
from app.db.models.source import SourceEntity
from app.db.repository.client import ClientRepository
from app.db.repository.organization import OrganizationRepository
from app.db.repository.query_builder.context.source_context import (
    SourceClientQueryContext,
    SourceOrganizationQueryContext,
    SourceQueryContext,
)
from app.db.repository.source import SourceRepository


def test_find_one_should_succeed(
    source_entity: SourceEntity,
    organization_entity: OrganizationEntity,
    organization_repository: OrganizationRepository,
    source_repository: SourceRepository,
) -> None:
    with organization_repository.db_session:
        organization_entity.sources.append(source_entity)
        org = organization_repository.add_one(organization_entity)
        src = org.sources[0]

    with source_repository.db_session:
        actual = source_repository.find_one(src.id, org.id)

        assert actual is not None
        assert actual.id == src.id
        assert actual.source_id == src.source_id


def test_find_one_should_return_none_on_wrong_id(
    source_entity: SourceEntity,
    organization_entity: OrganizationEntity,
    organization_repository: OrganizationRepository,
    source_repository: SourceRepository,
) -> None:
    with organization_repository.db_session:
        organization_entity.sources.append(source_entity)
        org = organization_repository.add_one(organization_entity)

    with source_repository.db_session:
        actual = source_repository.find_one(uuid4(), org.id)

        assert actual is None


def test_find_one_should_return_none_on_wrong_organization_id(
    source_entity: SourceEntity,
    organization_entity: OrganizationEntity,
    organization_repository: OrganizationRepository,
    source_repository: SourceRepository,
) -> None:
    with organization_repository.db_session:
        organization_entity.sources.append(source_entity)
        org = organization_repository.add_one(organization_entity)
        src = org.sources[0]

    with source_repository.db_session:
        actual = source_repository.find_one(src.id, uuid4())

        assert actual is None


def test_find_many_should_return_all(
    source_entity: SourceEntity,
    organization_entity: OrganizationEntity,
    client_entity: ClientEntity,
    organization_repository: OrganizationRepository,
    source_repository: SourceRepository,
    client_repository: ClientRepository,
) -> None:
    src_entity_2 = SourceEntity(source_id="source-2", name="Test Source 2")
    src_entity_3 = SourceEntity(source_id="source_3", name="Test Source 3")

    with organization_repository.db_session:
        organization_entity.sources.extend([source_entity, src_entity_2, src_entity_3])
        client_entity.sources.extend([src_entity_2, src_entity_3])
        organization_entity.clients.append(client_entity)
        organization_repository.add_one(organization_entity)

    with source_repository.db_session:
        ctx = SourceQueryContext.default()
        results = source_repository.find_many(ctx)

        assert len(results) == 3


def test_find_many_should_match_on_source_params(
    source_entity: SourceEntity,
    organization_entity: OrganizationEntity,
    client_entity: ClientEntity,
    organization_repository: OrganizationRepository,
    source_repository: SourceRepository,
    client_repository: ClientRepository,
) -> None:
    src_entity_2 = SourceEntity(source_id="source-2", name="Test Source 2")
    src_entity_3 = SourceEntity(source_id="source_3", name="Test Source 3")

    with organization_repository.db_session:
        organization_entity.sources.extend([source_entity, src_entity_2, src_entity_3])
        client_entity.sources.extend([src_entity_2, src_entity_3])
        organization_entity.clients.append(client_entity)
        org = organization_repository.add_one(organization_entity)

    with source_repository.db_session:
        ctx = SourceQueryContext(source_id=source_entity.source_id)
        results = source_repository.find_many(ctx)

        assert len(results) == 1
        actual = results[0]

        assert actual.source_id == source_entity.source_id
        assert actual.organization_id == org.id


def test_find_many_should_return_empty_list_on_no_match(
    source_entity: SourceEntity,
    organization_entity: OrganizationEntity,
    organization_repository: OrganizationRepository,
    source_repository: SourceRepository,
) -> None:
    with organization_repository.db_session:
        organization_entity.sources.append(source_entity)
        org = organization_repository.add_one(organization_entity)

    with source_repository.db_session:
        ctx = SourceQueryContext(id=uuid4(), organization_id=org.id)
        results = source_repository.find_many(ctx)

        assert results == []


def test_find_many_should_only_load_based_on_ctx_attr(
    source_entity: SourceEntity,
    organization_entity: OrganizationEntity,
    client_entity: ClientEntity,
    organization_repository: OrganizationRepository,
    source_repository: SourceRepository,
    client_repository: ClientRepository,
) -> None:
    with organization_repository.db_session:
        organization_entity.sources.append(source_entity)
        client_entity.sources.append(source_entity)
        organization_entity.clients.append(client_entity)

        org = organization_repository.add_one(organization_entity)

    with source_repository.db_session as session:
        ctx = SourceQueryContext(organization_ctx=SourceOrganizationQueryContext(id=org.id))
        result = source_repository.find_many(ctx)
        actual_src = result[0]

        with pytest.raises(InvalidRequestError):
            _ = actual_src.clients

        session.session.flush()
        session.session.expire_all()

        ctx = SourceQueryContext(client_ctx=SourceClientQueryContext(name=client_entity.name))
        results = source_repository.find_many(ctx)

        actual_src = results[0]

        with pytest.raises(InvalidRequestError):
            _ = actual_src.organization


def test_find_many_should_return_based_on_include_deleted_flag(
    source_entity: SourceEntity,
    organization_entity: OrganizationEntity,
    organization_repository: OrganizationRepository,
    source_repository: SourceRepository,
) -> None:
    source_entity.deleted_at = datetime.now()
    with organization_repository.db_session:
        organization_entity.sources.append(source_entity)
        org = organization_repository.add_one(organization_entity)

    with source_repository.db_session:
        ctx = SourceQueryContext(organization_id=org.id)
        non_deleted_result = source_repository.find_many(ctx)

        assert non_deleted_result == []

        deleted_results = source_repository.find_many(ctx, include_deleted=True)

        assert len(deleted_results) == 1


def test_find_should_return_result_based_on_source_attr(
    source_entity: SourceEntity,
    organization_entity: OrganizationEntity,
    organization_repository: OrganizationRepository,
    source_repository: SourceRepository,
) -> None:
    with organization_repository.db_session:
        organization_entity.sources.append(source_entity)
        org = organization_repository.add_one(organization_entity)

    with source_repository.db_session:
        ctx = SourceQueryContext(source_id=source_entity.source_id)

        actual = source_repository.find(ctx)

        assert actual is not None
        assert actual.source_id == source_entity.source_id
        assert actual.organization_id == org.id


def test_find_should_return_none_when_no_match_found(
    source_entity: SourceEntity,
    organization_entity: OrganizationEntity,
    organization_repository: OrganizationRepository,
    source_repository: SourceRepository,
) -> None:
    with organization_repository.db_session:
        organization_entity.sources.append(source_entity)
        org = organization_repository.add_one(organization_entity)

    with source_repository.db_session:
        ctx = SourceQueryContext(id=uuid4(), organization_id=org.id)

        actual = source_repository.find(ctx)

        assert actual is None


def test_find_should_return_based_on_children_attr(
    source_entity: SourceEntity,
    organization_entity: OrganizationEntity,
    client_entity: ClientEntity,
    organization_repository: OrganizationRepository,
    source_repository: SourceRepository,
    client_repository: ClientRepository,
) -> None:
    src_entity_2 = SourceEntity(source_id="source-2", name="Test Source 2")
    with organization_repository.db_session:
        organization_entity.sources.extend([source_entity, src_entity_2])
        client_entity.sources.append(source_entity)
        organization_entity.clients.append(client_entity)
        org = organization_repository.add_one(organization_entity)

    with source_repository.db_session:
        ctx = SourceQueryContext(
            source_id=source_entity.source_id,
            client_ctx=SourceClientQueryContext(organization_id=org.id, name=client_entity.name),
        )

        client_src = source_repository.find(ctx)

        assert client_src is not None

        assert client_src.source_id == source_entity.source_id
        assert client_src.organization_id == org.id

        ctx = SourceQueryContext(
            source_id=src_entity_2.source_id, organization_ctx=SourceOrganizationQueryContext(id=org.id)
        )

        actual_src_2 = source_repository.find(ctx)

        assert actual_src_2 is not None
        assert actual_src_2.organization_id == org.id
        assert actual_src_2.source_id == src_entity_2.source_id


def test_find_should_load_only_what_is_requested_in_ctx(
    source_entity: SourceEntity,
    organization_entity: OrganizationEntity,
    client_entity: ClientEntity,
    organization_repository: OrganizationRepository,
    source_repository: SourceRepository,
    client_repository: ClientRepository,
) -> None:
    with organization_repository.db_session:
        organization_entity.sources.append(source_entity)
        client_entity.sources.append(source_entity)
        organization_entity.clients.append(client_entity)
        org = organization_repository.add_one(organization_entity)

    with source_repository.db_session as session:
        ctx = SourceQueryContext(client_ctx=SourceClientQueryContext(name=client_entity.name, organization_id=org.id))

        actual = source_repository.find(ctx)

        assert actual is not None
        with pytest.raises(InvalidRequestError):
            _ = actual.organization

        session.session.flush()
        session.session.expire_all()

        ctx = SourceQueryContext(
            source_id=source_entity.source_id,
            client_ctx=SourceClientQueryContext(
                organization_id=org.id,
                name=client_entity.name,
            ),
        )

        actual = source_repository.find(ctx)
        assert actual is not None
        with pytest.raises(InvalidRequestError):
            _ = actual.organization
