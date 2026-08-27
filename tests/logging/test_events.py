import logging

import pytest
from gfmodules.logging import DefaultEventCatalogue, LoggingStreams, declared_events
from gfmodules.logging.testing import assert_catalogue_complete

from app.logging.events import ACT_CN, Log

_APP = LoggingStreams.APP
_SIEM = LoggingStreams.SIEM


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
        ("ACCESS_REQUEST", "094500"),
        ("CLIENT_ONBOARDED", "100607"),
        ("CLIENT_OFFBOARDED", "100608"),
        ("CREDENTIAL_COUPLED", "100609"),
    ],
)
def test_events_carry_the_id_the_nvi_spec_assigns(name: str, event_id: str) -> None:
    assert getattr(Log, name).event_id == event_id


def test_the_per_route_access_ids_cover_every_mutating_beheer_route() -> None:
    assert Log.access_event_id[("POST", "/organizations")] == "100700"
    assert Log.access_event_id[("DELETE", "/organizations/{organization_id}/clients/{id}")] == "100705"


class TestTheOverriddenSlots:
    def test_the_access_record_adds_the_acting_client(self) -> None:
        added = set(Log.ACCESS_REQUEST.fields[_APP]) - set(DefaultEventCatalogue.ACCESS_REQUEST.fields[_APP])
        assert added == {ACT_CN.name}

    def test_every_other_system_slot_keeps_the_shared_routing(self) -> None:
        rerouted = {
            name
            for name, event in vars(Log).items()
            if not name.startswith("_")
            and name in vars(DefaultEventCatalogue)
            and event.replace(event_id="") != getattr(DefaultEventCatalogue, name)
        }
        assert rerouted == {"ACCESS_REQUEST"}


class TestStreamRoutingIsDeclared:
    def test_no_event_routes_to_public_inspect(self) -> None:
        assert [name for name, event in declared_events(Log) if LoggingStreams.PUBLIC_INSPECT in event.streams] == []

    def test_every_siem_event_narrows_its_fields(self) -> None:
        for name, event in declared_events(Log):
            if _SIEM in event.streams:
                assert event.fields, f"{name} routes to SIEM without a field allow-list"

    def test_onboarding_keeps_the_oin_out_of_siem(self) -> None:
        assert "oin" in Log.CLIENT_ONBOARDED.fields[_APP]
        assert "oin" not in Log.CLIENT_ONBOARDED.fields[_SIEM]

    def test_the_health_error_detail_is_app_only(self) -> None:
        assert Log.HEALTH_UNHEALTHY.level == logging.ERROR
        assert "error_detail" in Log.HEALTH_UNHEALTHY.fields[_APP]
        assert "error_detail" not in Log.HEALTH_UNHEALTHY.fields[_SIEM]
