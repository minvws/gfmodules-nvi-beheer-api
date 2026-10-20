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
        }
    ):
        yield _route


class TestClientCreated:
    @pytest.fixture
    def routed(self, route: Any) -> Routed:
        return dict(
            route(
                Log.CLIENT_CREATED,
                "created",
                organization_id="org-1",
                client_id="client-1",
                scopes="nvi:localize nvi:read",
                certificate_ids=["cert-1"],
                source_ids=["src-1"],
            )
        )

    def test_app_receives_the_client_and_its_couplings(self, routed: Routed) -> None:
        message = routed[LoggingStreams.APP][0]
        assert message["organization_id"] == "org-1"
        assert message["client_id"] == "client-1"
        assert message["scopes"] == "nvi:localize nvi:read"
        assert message["certificate_ids"] == ["cert-1"]
        assert message["source_ids"] == ["src-1"]

    def test_siem_receives_the_client_and_its_scopes_but_not_the_couplings(self, routed: Routed) -> None:
        message = routed[LoggingStreams.SIEM][0]
        assert message["organization_id"] == "org-1"
        assert message["client_id"] == "client-1"
        assert message["scopes"] == "nvi:localize nvi:read"
        assert_fields_absent(routed[LoggingStreams.SIEM], "certificate_ids", "source_ids")

    def test_public_inspect_receives_nothing(self, routed: Routed) -> None:
        assert routed[LoggingStreams.PUBLIC_INSPECT] == []

    def test_correlation_metadata_is_retained_in_every_routed_stream(self, routed: Routed) -> None:
        for stream in (LoggingStreams.APP, LoggingStreams.SIEM):
            message = routed[stream][0]
            assert message["request_id"] == "req-1"
            assert message["ip"] == "10.0.0.1"
            assert message["correlation_id"] == "corr-1"


class TestCertificateAssigned:
    def test_the_domain_never_reaches_siem(self, route: Any) -> None:
        routed: Routed = route(
            Log.CLIENT_CERTIFICATE_ASSIGNED,
            "assigned",
            organization_id="org-1",
            client_id="client-1",
            certificate_id="cert-1",
            certificate_organization_identifier=_OIN,
            domain="example.com",
        )

        assert routed[LoggingStreams.APP][0]["domain"] == "example.com"
        assert routed[LoggingStreams.SIEM][0]["certificate_organization_identifier"] == _OIN
        assert routed[LoggingStreams.SIEM][0]["client_id"] == "client-1"
        assert_fields_absent(routed[LoggingStreams.SIEM], "domain")


class TestClientResolved:
    def test_the_matched_domain_and_source_never_reach_siem(self, route: Any) -> None:
        routed: Routed = route(
            Log.CLIENT_RESOLVED,
            "resolved",
            client_id="client-1",
            ura_number=_URA,
            certificate_organization_identifier=_OIN,
            matched_domain="example.com",
            source_id="src-1",
            scopes="nvi:read",
        )

        assert routed[LoggingStreams.APP][0]["matched_domain"] == "example.com"
        assert routed[LoggingStreams.APP][0]["source_id"] == "src-1"
        assert routed[LoggingStreams.SIEM][0]["ura_number"] == _URA
        assert routed[LoggingStreams.SIEM][0]["scopes"] == "nvi:read"
        assert_fields_absent(routed[LoggingStreams.SIEM], "matched_domain", "source_id")


class TestClientResolveDenied:
    def test_siem_learns_who_was_denied_and_why_but_not_the_presented_domains(self, route: Any) -> None:
        routed: Routed = route(
            Log.CLIENT_RESOLVE_DENIED,
            "denied",
            client_id="client-1",
            ura_number=_URA,
            certificate_organization_identifier=_OIN,
            certificate_domains=["example.com"],
            source_id="src-1",
            error_reason="certificate_mismatch",
        )

        assert routed[LoggingStreams.APP][0]["certificate_domains"] == ["example.com"]
        siem = routed[LoggingStreams.SIEM][0]
        assert (siem["client_id"], siem["ura_number"], siem["error_reason"]) == (
            "client-1",
            _URA,
            "certificate_mismatch",
        )
        assert_fields_absent(routed[LoggingStreams.SIEM], "certificate_domains", "source_id")


class TestRequestRefused:
    def test_reaches_app_and_siem_with_the_error_type_and_status(self, route: Any) -> None:
        routed: Routed = route(Log.REQUEST_REFUSED, "refused", error_type="ConflictError", status_code=409)

        for stream in (LoggingStreams.APP, LoggingStreams.SIEM):
            assert routed[stream][0]["error_type"] == "ConflictError"
            assert routed[stream][0]["status_code"] == 409
        assert routed[LoggingStreams.PUBLIC_INSPECT] == []


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
    def test_reaches_the_app_stream_only(self, route: Any) -> None:
        routed: Routed = route(Log.ACCESS_REQUEST, "access", status_code=201, duration_ms=5)

        message = routed[LoggingStreams.APP][0]
        assert message["endpoint"] == "/organizations"
        assert message["method"] == "POST"
        assert message["status_code"] == 201
        assert message["duration_ms"] == 5

        assert routed[LoggingStreams.PUBLIC_INSPECT] == []
        assert routed[LoggingStreams.SIEM] == []
