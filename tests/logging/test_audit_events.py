from collections.abc import Iterator
from uuid import uuid4

import pytest
from gfmodules.logging.testing import CapturedRecords, assert_event_emitted, capture_records

from app.exceptions import EntityHasActiveMembersError, ResolveError
from app.logging.events import Log
from app.models.certificates import CertificateCreate, CertificateUpdate
from app.models.client import ClientCreate, ClientResolveRequest, ClientUpdate
from app.models.organization import Organization, OrganizationCreate, OrganizationUpdate
from app.models.scopes import AuthorizationScope
from app.models.source import SourceCreate, SourceUpdate
from app.services.certificate.client_certificate import ClientCertificateService
from app.services.certificate.organization_certificate import OrganizationCertificateService
from app.services.client import ClientService
from app.services.organization import OrganizationService
from app.services.source.client_source import ClientSourceService
from app.services.source.organization_source import OrganizationSourceService
from tests.conftest import (
    SECOND_OIN,
    TEST_CLIENT_NAME,
    TEST_DOMAIN,
    TEST_EXTERNAL_ID,
    TEST_OIN,
    TEST_ORG_NAME,
    TEST_SOURCE_ID,
    TEST_SOURCE_NAME,
)


@pytest.fixture
def records() -> Iterator[CapturedRecords]:
    with capture_records("app") as captured:
        yield captured


@pytest.fixture
def organization(organization_service: OrganizationService) -> Organization:
    return organization_service.create_one(
        OrganizationCreate(external_id=TEST_EXTERNAL_ID, name=TEST_ORG_NAME, scopes=[AuthorizationScope.READ])
    )


@pytest.fixture
def populated_organization(
    organization_service: OrganizationService, org_create_dto_1: OrganizationCreate
) -> Organization:
    return organization_service.create_one(org_create_dto_1)


class TestOrganizationEvents:
    def test_creating_an_organization_logs_it(self, records: CapturedRecords, organization: Organization) -> None:
        assert_event_emitted(
            records,
            Log.ORGANIZATION_CREATED,
            organization_id=str(organization.id),
            ura_number=str(TEST_EXTERNAL_ID),
            scopes="nvi:read",
        )

    def test_creating_an_organization_logs_everything_created_with_it(
        self, records: CapturedRecords, populated_organization: Organization
    ) -> None:
        assert populated_organization.certificates is not None
        assert populated_organization.sources is not None
        assert populated_organization.clients is not None
        client = populated_organization.clients[0]
        assert client.certificates is not None
        assert client.sources is not None

        assert len(records.for_event(Log.CERTIFICATE_CREATED)) == len(populated_organization.certificates)
        assert len(records.for_event(Log.SOURCE_CREATED)) == len(populated_organization.sources)
        assert_event_emitted(
            records,
            Log.CLIENT_CREATED,
            organization_id=str(populated_organization.id),
            client_id=str(client.id),
            scopes="nvi:create nvi:read",
            certificate_ids=[str(c.id) for c in client.certificates],
            source_ids=[s.source_id for s in client.sources],
        )

    def test_updating_an_organization_logs_the_new_scopes(
        self, records: CapturedRecords, organization_service: OrganizationService, organization: Organization
    ) -> None:
        organization_service.update_one(
            organization.id,
            OrganizationUpdate(
                external_id=TEST_EXTERNAL_ID,
                name="Renamed",
                scopes=[AuthorizationScope.READ, AuthorizationScope.CREATE],
            ),
        )

        assert_event_emitted(
            records,
            Log.ORGANIZATION_UPDATED,
            organization_id=str(organization.id),
            ura_number=str(TEST_EXTERNAL_ID),
            scopes="nvi:create nvi:read",
        )

    def test_an_update_that_changes_nothing_is_not_logged(
        self, records: CapturedRecords, organization_service: OrganizationService, organization: Organization
    ) -> None:
        organization_service.update_one(
            organization.id,
            OrganizationUpdate(external_id=TEST_EXTERNAL_ID, name=TEST_ORG_NAME, scopes=[AuthorizationScope.READ]),
        )

        assert records.for_event(Log.ORGANIZATION_UPDATED) == []

    def test_deleting_an_organization_logs_it(
        self, records: CapturedRecords, organization_service: OrganizationService, organization: Organization
    ) -> None:
        organization_service.delete_one(organization.id)

        assert_event_emitted(
            records,
            Log.ORGANIZATION_DELETED,
            organization_id=str(organization.id),
            ura_number=str(TEST_EXTERNAL_ID),
        )

    def test_a_refused_delete_is_not_logged_as_deleted(
        self,
        records: CapturedRecords,
        organization_service: OrganizationService,
        populated_organization: Organization,
    ) -> None:
        with pytest.raises(EntityHasActiveMembersError):
            organization_service.delete_one(populated_organization.id)

        assert records.for_event(Log.ORGANIZATION_DELETED) == []


class TestClientEvents:
    def test_creating_a_client_logs_it(
        self, records: CapturedRecords, client_service: ClientService, organization: Organization
    ) -> None:
        client = client_service.create_one(
            organization.id, ClientCreate(name=TEST_CLIENT_NAME, scopes=[AuthorizationScope.READ])
        )

        assert_event_emitted(
            records,
            Log.CLIENT_CREATED,
            organization_id=str(organization.id),
            client_id=str(client.id),
            scopes="nvi:read",
            certificate_ids=[],
            source_ids=[],
        )

    def test_updating_a_client_logs_its_new_state(
        self, records: CapturedRecords, client_service: ClientService, organization: Organization
    ) -> None:
        client = client_service.create_one(organization.id, ClientCreate(name=TEST_CLIENT_NAME))

        client_service.update_one(
            client.id,
            organization.id,
            ClientUpdate(id=client.id, name="Renamed", scopes=[AuthorizationScope.READ]),
        )

        assert_event_emitted(
            records,
            Log.CLIENT_UPDATED,
            organization_id=str(organization.id),
            client_id=str(client.id),
            scopes="nvi:read",
        )

    def test_deleting_a_client_logs_it(
        self, records: CapturedRecords, client_service: ClientService, organization: Organization
    ) -> None:
        client = client_service.create_one(organization.id, ClientCreate(name=TEST_CLIENT_NAME))

        client_service.delete_one(client.id, organization.id)

        assert_event_emitted(
            records, Log.CLIENT_DELETED, organization_id=str(organization.id), client_id=str(client.id)
        )


class TestCertificateEvents:
    def test_creating_a_certificate_logs_it(
        self,
        records: CapturedRecords,
        organization_certificate_service: OrganizationCertificateService,
        organization: Organization,
    ) -> None:
        certificate = organization_certificate_service.create_one(
            organization.id, CertificateCreate(organization_identifier=TEST_OIN, domain=TEST_DOMAIN)
        )

        assert_event_emitted(
            records,
            Log.CERTIFICATE_CREATED,
            organization_id=str(organization.id),
            certificate_id=str(certificate.id),
            certificate_organization_identifier=str(TEST_OIN),
            domain=TEST_DOMAIN,
        )

    def test_updating_a_certificate_logs_its_new_identifier(
        self,
        records: CapturedRecords,
        organization_certificate_service: OrganizationCertificateService,
        organization: Organization,
    ) -> None:
        certificate = organization_certificate_service.create_one(
            organization.id, CertificateCreate(organization_identifier=TEST_OIN, domain=TEST_DOMAIN)
        )

        organization_certificate_service.update_one(
            certificate.id,
            organization.id,
            CertificateUpdate(id=certificate.id, organization_identifier=SECOND_OIN, domain=TEST_DOMAIN),
        )

        assert_event_emitted(
            records,
            Log.CERTIFICATE_UPDATED,
            certificate_id=str(certificate.id),
            certificate_organization_identifier=str(SECOND_OIN),
        )

    def test_deleting_a_certificate_logs_it(
        self,
        records: CapturedRecords,
        organization_certificate_service: OrganizationCertificateService,
        organization: Organization,
    ) -> None:
        certificate = organization_certificate_service.create_one(
            organization.id, CertificateCreate(organization_identifier=TEST_OIN, domain=TEST_DOMAIN)
        )

        organization_certificate_service.delete_one(organization.id, certificate.id)

        assert_event_emitted(
            records, Log.CERTIFICATE_DELETED, organization_id=str(organization.id), certificate_id=str(certificate.id)
        )

    def test_assigning_and_unassigning_a_certificate_logs_both(
        self,
        records: CapturedRecords,
        organization_service: OrganizationService,
        client_certificate_service: ClientCertificateService,
        cert_create_dto_1: CertificateCreate,
    ) -> None:
        organization = organization_service.create_one(
            OrganizationCreate(
                external_id=TEST_EXTERNAL_ID,
                name=TEST_ORG_NAME,
                certificates=[cert_create_dto_1],
                clients=[ClientCreate(name=TEST_CLIENT_NAME)],
            )
        )
        assert organization.certificates is not None
        assert organization.clients is not None
        certificate, client = organization.certificates[0], organization.clients[0]

        client_certificate_service.assign_one(organization.id, client.id, certificate.id)
        client_certificate_service.unassign_one(organization.id, client.id, certificate.id)

        for event in (Log.CLIENT_CERTIFICATE_ASSIGNED, Log.CLIENT_CERTIFICATE_UNASSIGNED):
            assert_event_emitted(
                records,
                event,
                organization_id=str(organization.id),
                client_id=str(client.id),
                certificate_id=str(certificate.id),
                domain=TEST_DOMAIN,
            )


class TestSourceEvents:
    def test_creating_updating_and_deleting_a_source_logs_each(
        self,
        records: CapturedRecords,
        organization_source_service: OrganizationSourceService,
        organization: Organization,
    ) -> None:
        source = organization_source_service.create_one(
            organization.id, SourceCreate(source_id=TEST_SOURCE_ID, name=TEST_SOURCE_NAME)
        )
        organization_source_service.update_one(
            organization.id, source.id, SourceUpdate(id=source.id, source_id="renamed-source", name=TEST_SOURCE_NAME)
        )
        organization_source_service.delete_one(organization.id, source.id)

        organization_id = str(organization.id)
        assert_event_emitted(records, Log.SOURCE_CREATED, organization_id=organization_id, source_id=TEST_SOURCE_ID)
        assert_event_emitted(records, Log.SOURCE_UPDATED, organization_id=organization_id, source_id="renamed-source")
        assert_event_emitted(records, Log.SOURCE_DELETED, organization_id=organization_id, source_id="renamed-source")

    def test_assigning_and_unassigning_a_source_logs_both(
        self,
        records: CapturedRecords,
        organization_service: OrganizationService,
        client_source_service: ClientSourceService,
        source_create_dto_1: SourceCreate,
    ) -> None:
        organization = organization_service.create_one(
            OrganizationCreate(
                external_id=TEST_EXTERNAL_ID,
                name=TEST_ORG_NAME,
                sources=[source_create_dto_1],
                clients=[ClientCreate(name=TEST_CLIENT_NAME)],
            )
        )
        assert organization.sources is not None
        assert organization.clients is not None
        source, client = organization.sources[0], organization.clients[0]

        client_source_service.assign_one(organization.id, client.id, source.id)
        client_source_service.unassign_one(organization.id, client.id, source.id)

        for event in (Log.CLIENT_SOURCE_ASSIGNED, Log.CLIENT_SOURCE_UNASSIGNED):
            assert_event_emitted(
                records,
                event,
                organization_id=str(organization.id),
                client_id=str(client.id),
                source_id=source.source_id,
            )


class TestResolveEvents:
    @pytest.fixture
    def request_for(self, populated_organization: Organization) -> ClientResolveRequest:
        assert populated_organization.clients is not None
        return ClientResolveRequest(
            client_id=populated_organization.clients[0].id,
            organization_external_id=TEST_EXTERNAL_ID,
            certificate_organization_identifier=TEST_OIN,
            certificate_domains=[TEST_DOMAIN],
            source_id=TEST_SOURCE_ID,
        )

    def test_a_resolved_client_is_logged_with_its_granted_scopes(
        self, records: CapturedRecords, client_service: ClientService, request_for: ClientResolveRequest
    ) -> None:
        response = client_service.resolve(request_for)

        assert_event_emitted(
            records,
            Log.CLIENT_RESOLVED,
            client_id=str(request_for.client_id),
            ura_number=str(TEST_EXTERNAL_ID),
            certificate_organization_identifier=str(TEST_OIN),
            matched_domain=TEST_DOMAIN,
            source_id=TEST_SOURCE_ID,
            scopes=response.scopes,
        )

    @pytest.mark.parametrize(
        "change,reason",
        [
            ({"client_id": uuid4()}, "client_not_found"),
            ({"certificate_domains": ["unknown.example"]}, "certificate_mismatch"),
            ({"source_id": "unknown-source"}, "source_not_linked"),
        ],
    )
    def test_a_denied_resolve_is_logged_with_why_it_was_denied(
        self,
        records: CapturedRecords,
        client_service: ClientService,
        request_for: ClientResolveRequest,
        change: dict[str, object],
        reason: str,
    ) -> None:
        denied = request_for.model_copy(update=change)

        with pytest.raises(ResolveError):
            client_service.resolve(denied)

        assert_event_emitted(
            records,
            Log.CLIENT_RESOLVE_DENIED,
            client_id=str(denied.client_id),
            ura_number=str(TEST_EXTERNAL_ID),
            certificate_organization_identifier=str(TEST_OIN),
            certificate_domains=denied.certificate_domains,
            source_id=denied.source_id,
            error_reason=reason,
        )
        assert records.for_event(Log.CLIENT_RESOLVED) == []
