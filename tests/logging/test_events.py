import logging

import pytest
from gfmodules.logging import DefaultEventCatalogue, LoggingStreams, declared_events
from gfmodules.logging.testing import assert_catalogue_complete
from pytest_mock import MockerFixture

from app import application
from app.config import set_config
from app.logging.events import ACTOR, Log
from tests.test_config import get_test_config

_APP = LoggingStreams.APP
_SIEM = LoggingStreams.SIEM
_GIVEN_THE_ACTOR = ("ACCESS_REQUEST", "SYS_UNHANDLED_EXCEPTION")


def test_the_catalogue_fills_every_required_slot() -> None:
    """A slot left unfilled is invisible to mypy, so this is what catches it."""
    assert_catalogue_complete(Log)


@pytest.mark.parametrize(
    "name,event_id",
    [
        ("HEALTH_UNHEALTHY", "100600"),
        ("SYS_APP_STARTED", "100601"),
        ("SYS_APP_STOPPED", "100602"),
        ("SYS_APP_CRASHED", "100602"),
        ("DB_CONNECTION_FAILED", "100603"),
        ("SYS_UNHANDLED_EXCEPTION", "100604"),
        ("DB_SCHEMA_ERROR", "100605"),
        ("SYS_MISSING_CORRELATION_ID", "100606"),
        ("ORGANIZATION_CREATED", "100607"),
        ("ORGANIZATION_UPDATED", "100608"),
        ("ORGANIZATION_DELETED", "100609"),
        ("CLIENT_CREATED", "100610"),
        ("CLIENT_UPDATED", "100611"),
        ("CLIENT_DELETED", "100612"),
        ("CERTIFICATE_CREATED", "100613"),
        ("CERTIFICATE_UPDATED", "100614"),
        ("CERTIFICATE_DELETED", "100615"),
        ("CLIENT_CERTIFICATE_ASSIGNED", "100616"),
        ("CLIENT_CERTIFICATE_UNASSIGNED", "100617"),
        ("SOURCE_CREATED", "100618"),
        ("SOURCE_UPDATED", "100619"),
        ("SOURCE_DELETED", "100620"),
        ("CLIENT_SOURCE_ASSIGNED", "100621"),
        ("CLIENT_SOURCE_UNASSIGNED", "100622"),
        ("CLIENT_RESOLVED", "100623"),
        ("REQUEST_REFUSED", "100624"),
        ("CLIENT_RESOLVE_DENIED", "100625"),
        ("DB_OPERATION_FAILED", "100626"),
        ("REQUEST_FORBIDDEN", "100627"),
        ("ACCESS_REQUEST", "100"),
    ],
)
def test_events_carry_the_id_the_nvi_spec_assigns(name: str, event_id: str) -> None:
    assert getattr(Log, name).event_id == event_id


def test_no_two_application_events_share_an_id() -> None:
    ids = [event.event_id for name, event in declared_events(Log) if name != "SYS_APP_CRASHED"]
    assert len(ids) == len(set(ids))


class TestAccessEventIds:
    @pytest.fixture
    def mutating_routes(self, mocker: MockerFixture) -> set[tuple[str, str]]:
        mocker.patch("app.application.container.configure")
        set_config(get_test_config())
        paths = application.setup_fastapi().openapi()["paths"]
        return {
            (method.upper(), path)
            for path, operations in paths.items()
            for method in operations
            if method in {"post", "put", "patch", "delete"}
        }

    def test_every_mutating_route_has_an_access_id(self, mutating_routes: set[tuple[str, str]]) -> None:
        assert mutating_routes - Log.access_event_id.keys() == set()

    def test_every_access_id_belongs_to_a_mutating_route(self, mutating_routes: set[tuple[str, str]]) -> None:
        assert Log.access_event_id.keys() - mutating_routes == set()

    def test_no_two_routes_share_an_access_id(self) -> None:
        ids = list(Log.access_event_id.values())
        assert len(ids) == len(set(ids))


class TestTheOverriddenSlots:
    def test_every_other_system_slot_keeps_the_shared_routing(self) -> None:
        rerouted = {
            name
            for name, event in vars(Log).items()
            if not name.startswith("_")
            and name in vars(DefaultEventCatalogue)
            and event.replace(event_id="") != getattr(DefaultEventCatalogue, name).replace(event_id="")
        }
        assert rerouted == set(_GIVEN_THE_ACTOR)

    @pytest.mark.parametrize("name", _GIVEN_THE_ACTOR)
    def test_a_rerouted_slot_only_adds_who_made_the_request(self, name: str) -> None:
        shared = getattr(DefaultEventCatalogue, name)
        event = getattr(Log, name)
        assert event.streams == shared.streams
        assert event.fields == {stream: (*shared.fields[stream], ACTOR.name) for stream in shared.streams}


class TestStreamRoutingIsDeclared:
    def test_no_event_routes_to_public_inspect(self) -> None:
        assert [name for name, event in declared_events(Log) if LoggingStreams.PUBLIC_INSPECT in event.streams] == []

    def test_every_siem_event_narrows_its_fields(self) -> None:
        for name, event in declared_events(Log):
            if _SIEM in event.streams:
                assert event.fields, f"{name} routes to SIEM without a field allow-list"

    def test_every_request_event_carries_who_made_the_request(self) -> None:
        for name, event in declared_events(Log):
            if name.startswith(("SYS_", "HEALTH_", "DB_")):
                continue
            for stream in event.streams:
                assert ACTOR.name in event.fields[stream], f"{name} drops the actor on {stream}"

    def test_client_couplings_reach_siem(self) -> None:
        for event in (Log.CLIENT_CREATED, Log.CLIENT_UPDATED, Log.CLIENT_DELETED):
            assert {"certificate_ids", "source_ids"} <= set(event.fields[_SIEM])

    def test_the_certificate_domain_is_app_only(self) -> None:
        for event in (Log.CERTIFICATE_CREATED, Log.CLIENT_CERTIFICATE_ASSIGNED):
            assert "domain" in event.fields[_APP]
            assert "domain" not in event.fields[_SIEM]

    def test_a_successful_resolve_stays_out_of_siem(self) -> None:
        assert Log.CLIENT_RESOLVED.streams == (_APP,)

    def test_the_presented_domains_and_source_of_a_denied_resolve_are_app_only(self) -> None:
        assert {"certificate_domains", "source_id"} <= set(Log.CLIENT_RESOLVE_DENIED.fields[_APP])
        assert {"certificate_domains", "source_id"}.isdisjoint(Log.CLIENT_RESOLVE_DENIED.fields[_SIEM])

    def test_only_a_forbidden_request_reaches_siem(self) -> None:
        assert Log.REQUEST_REFUSED.streams == (_APP,)
        assert Log.REQUEST_FORBIDDEN.streams == (_APP, _SIEM)

    def test_the_health_error_detail_is_app_only(self) -> None:
        assert Log.HEALTH_UNHEALTHY.level == logging.ERROR
        assert "error_detail" in Log.HEALTH_UNHEALTHY.fields[_APP]
        assert "error_detail" not in Log.HEALTH_UNHEALTHY.fields[_SIEM]
