import logging
from collections.abc import Iterator
from contextlib import ExitStack
from typing import Any

import gfmodules.logging as gflog
import pytest
from gfmodules.logging import LogEvent, LoggingStreams, bind_context
from gfmodules.logging.testing import assert_fields_absent, capture_stream

from app.logging.events import Log

_LOGGER_NAME = "app.test_stream_routing"
_OIN = "00000001000000000001"
_URA = "12345678"

Routed = dict[LoggingStreams, list[dict[str, Any]]]


@pytest.fixture
def route() -> Iterator[Any]:
    logger = logging.getLogger(_LOGGER_NAME)

    def _route(event: LogEvent, message: str = "event", **fields: Any) -> Routed:
        with ExitStack() as stack:
            routed: Routed = {
                stream: stack.enter_context(capture_stream(stream, _LOGGER_NAME)) for stream in LoggingStreams
            }
            gflog.emit(logger, event, message, fields={**fields})
        return routed

    with bind_context(
        {
            "request_id": "req-1",
            "ip": "10.0.0.1",
            "endpoint": "/organizations",
            "method": "POST",
            "correlation_id": "corr-1",
            "gf-act-cn": "acting-client",
        }
    ):
        yield _route


class TestClientOnboarded:
    @pytest.fixture
    def routed(self, route: Any) -> Routed:
        return dict(
            route(
                Log.CLIENT_ONBOARDED,
                "onboarded",
                oin=_OIN,
                ura_number=_URA,
                source_identifier="src-1",
                approved_by="admin",
                scopes="read write",
            )
        )

    def test_app_receives_every_onboarding_field(self, routed: Routed) -> None:
        message = routed[LoggingStreams.APP][0]
        assert message["oin"] == _OIN
        assert message["ura_number"] == _URA
        assert message["source_identifier"] == "src-1"
        assert message["approved_by"] == "admin"
        assert message["scopes"] == "read write"

    def test_siem_receives_the_ura_and_scopes_and_nothing_else(self, routed: Routed) -> None:
        message = routed[LoggingStreams.SIEM][0]
        assert message["ura_number"] == _URA
        assert message["scopes"] == "read write"
        assert_fields_absent(routed[LoggingStreams.SIEM], "oin", "source_identifier", "approved_by")

    def test_public_inspect_receives_nothing(self, routed: Routed) -> None:
        assert routed[LoggingStreams.PUBLIC_INSPECT] == []

    def test_correlation_metadata_is_retained_in_every_routed_stream(self, routed: Routed) -> None:
        for stream in (LoggingStreams.APP, LoggingStreams.SIEM):
            message = routed[stream][0]
            assert message["request_id"] == "req-1"
            assert message["ip"] == "10.0.0.1"
            assert message["correlation_id"] == "corr-1"


class TestClientOffboarded:
    @pytest.fixture
    def routed(self, route: Any) -> Routed:
        return dict(
            route(
                Log.CLIENT_OFFBOARDED,
                "offboarded",
                oin=_OIN,
                ura_number=_URA,
                deactivated_by="admin",
                reason="contract ended",
            )
        )

    def test_app_receives_the_oin_and_the_reason(self, routed: Routed) -> None:
        message = routed[LoggingStreams.APP][0]
        assert message["oin"] == _OIN
        assert message["reason"] == "contract ended"

    def test_siem_receives_neither_the_oin_nor_the_reason(self, routed: Routed) -> None:
        message = routed[LoggingStreams.SIEM][0]
        assert message["ura_number"] == _URA
        assert message["deactivated_by"] == "admin"
        assert_fields_absent(routed[LoggingStreams.SIEM], "oin", "reason")


class TestHealthUnhealthy:
    def test_the_error_detail_never_reaches_siem(self, route: Any) -> None:
        routed: Routed = route(
            Log.HEALTH_UNHEALTHY,
            "unhealthy",
            component="database",
            status="error",
            error_detail="connection refused",
        )

        assert routed[LoggingStreams.APP][0]["error_detail"] == "connection refused"
        assert routed[LoggingStreams.SIEM][0]["component"] == "database"
        assert_fields_absent(routed[LoggingStreams.SIEM], "error_detail")


class TestAccessRequest:
    def test_reaches_the_app_stream_only_and_carries_the_acting_client(self, route: Any) -> None:
        routed: Routed = route(Log.ACCESS_REQUEST, "access", status_code=201, duration_ms=5)

        message = routed[LoggingStreams.APP][0]
        assert message["endpoint"] == "/organizations"
        assert message["method"] == "POST"
        assert message["status_code"] == 201
        assert message["duration_ms"] == 5
        assert message["gf-act-cn"] == "acting-client"

        assert routed[LoggingStreams.PUBLIC_INSPECT] == []
        assert routed[LoggingStreams.SIEM] == []
