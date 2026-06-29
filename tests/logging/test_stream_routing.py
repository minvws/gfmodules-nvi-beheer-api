"""Integration tests for per-field stream routing.

Wires up the PUBLIC_INSPECT (stroom 1), APP (stroom 2) and SIEM (stroom 3)
handlers the same way ``LogConfigBuilder`` does and asserts each stream only
receives the fields the app's own events assign to it. None of this app's
events route to PUBLIC_INSPECT, so that stream is expected to stay empty.
"""

import io
import json
import logging
from typing import Any, Iterator

import pytest

from app.logging.context import endpoint_var, ip_var, method_var, request_id_var
from app.logging.events import Log
from app.logging.filters import (
    AppFilter,
    LoggingStreams,
    PublicInspectFilter,
    SiemFilter,
)
from app.logging.formatter import JsonFormatter


@pytest.fixture
def streams() -> Iterator[tuple[logging.Logger, io.StringIO, io.StringIO, io.StringIO]]:
    pub_buf, app_buf, siem_buf = io.StringIO(), io.StringIO(), io.StringIO()

    pub_handler = logging.StreamHandler(pub_buf)
    pub_handler.addFilter(PublicInspectFilter())
    pub_handler.setFormatter(JsonFormatter(include_traces=False, stream=LoggingStreams.PUBLIC_INSPECT))

    app_handler = logging.StreamHandler(app_buf)
    app_handler.addFilter(AppFilter())
    app_handler.setFormatter(JsonFormatter(include_traces=False, stream=LoggingStreams.APP))

    siem_handler = logging.StreamHandler(siem_buf)
    siem_handler.addFilter(SiemFilter())
    siem_handler.setFormatter(JsonFormatter(include_traces=False, stream=LoggingStreams.SIEM))

    logger = logging.getLogger("app.test_stream_routing")
    logger.setLevel(logging.DEBUG)
    logger.handlers = [pub_handler, app_handler, siem_handler]
    logger.propagate = False

    tokens = [
        request_id_var.set("req-1"),
        ip_var.set("10.0.0.1"),
        endpoint_var.set("/token"),
        method_var.set("POST"),
    ]
    try:
        yield logger, pub_buf, app_buf, siem_buf
    finally:
        logger.handlers = []
        request_id_var.reset(tokens[0])
        ip_var.reset(tokens[1])
        endpoint_var.reset(tokens[2])
        method_var.reset(tokens[3])


def _messages(buf: io.StringIO) -> list[dict[str, Any]]:
    return [json.loads(line)["message"] for line in buf.getvalue().splitlines()]


def test_client_onboarded_routes_fields_per_stream(
    streams: tuple[logging.Logger, io.StringIO, io.StringIO, io.StringIO],
) -> None:
    logger, pub_buf, app_buf, siem_buf = streams
    Log.event(
        logger,
        Log.CLIENT_ONBOARDED,
        "onboarded",
        oin="00000001000000000001",
        ura_number="12345678",
        source_identifier="src-1",
        approved_by="admin",
        scopes="read write",
    )

    app_msg = _messages(app_buf)[0]
    siem_msg = _messages(siem_buf)[0]

    # APP (stroom 2) gets every onboarding field
    assert app_msg["oin"] == "00000001000000000001"
    assert app_msg["ura_number"] == "12345678"
    assert app_msg["source_identifier"] == "src-1"
    assert app_msg["approved_by"] == "admin"
    assert app_msg["scopes"] == "read write"

    # SIEM (stroom 3) gets ura_number + scopes only
    assert siem_msg["ura_number"] == "12345678"
    assert siem_msg["scopes"] == "read write"
    assert "oin" not in siem_msg
    assert "source_identifier" not in siem_msg
    assert "approved_by" not in siem_msg

    # CLIENT_ONBOARDED is not routed to PUB (stroom 1)
    assert pub_buf.getvalue() == ""

    # correlation metadata is retained in the routed streams
    for msg in (app_msg, siem_msg):
        assert msg["request_id"] == "req-1"
        assert msg["ip"] == "10.0.0.1"


def test_client_offboarded_routes_to_app_and_siem(
    streams: tuple[logging.Logger, io.StringIO, io.StringIO, io.StringIO],
) -> None:
    logger, pub_buf, app_buf, siem_buf = streams
    Log.event(
        logger,
        Log.CLIENT_OFFBOARDED,
        "offboarded",
        oin="00000001000000000001",
        ura_number="12345678",
        deactivated_by="admin",
        reason="contract ended",
    )

    app_msg = _messages(app_buf)[0]
    siem_msg = _messages(siem_buf)[0]

    # APP keeps oin + ura_number + deactivated_by + reason
    assert app_msg["oin"] == "00000001000000000001"
    assert app_msg["ura_number"] == "12345678"
    assert app_msg["deactivated_by"] == "admin"
    assert app_msg["reason"] == "contract ended"

    # SIEM keeps ura_number + deactivated_by, but NOT oin or reason
    assert siem_msg["ura_number"] == "12345678"
    assert siem_msg["deactivated_by"] == "admin"
    assert "oin" not in siem_msg
    assert "reason" not in siem_msg

    # CLIENT_OFFBOARDED is not routed to PUB (stroom 1)
    assert pub_buf.getvalue() == ""


def test_health_unhealthy_drops_error_detail_from_siem(
    streams: tuple[logging.Logger, io.StringIO, io.StringIO, io.StringIO],
) -> None:
    logger, pub_buf, app_buf, siem_buf = streams
    Log.event(
        logger,
        Log.HEALTH_UNHEALTHY,
        "unhealthy",
        component="database",
        status="down",
        error_detail="connection refused",
    )

    app_msg = _messages(app_buf)[0]
    siem_msg = _messages(siem_buf)[0]

    # APP keeps component + status + error_detail
    assert app_msg["component"] == "database"
    assert app_msg["status"] == "down"
    assert app_msg["error_detail"] == "connection refused"

    # SIEM keeps component + status, but drops the error detail
    assert siem_msg["component"] == "database"
    assert siem_msg["status"] == "down"
    assert "error_detail" not in siem_msg

    # HEALTH_UNHEALTHY is not routed to PUB (stroom 1)
    assert pub_buf.getvalue() == ""


def test_access_request_goes_to_app_only(
    streams: tuple[logging.Logger, io.StringIO, io.StringIO, io.StringIO],
) -> None:
    logger, pub_buf, app_buf, siem_buf = streams
    Log.event(logger, Log.ACCESS_REQUEST, "access", status_code=200, duration_ms=5)

    app_msg = _messages(app_buf)[0]
    assert app_msg["endpoint"] == "/token"
    assert app_msg["method"] == "POST"
    # off-spec extras are not forwarded to the stream
    assert "status_code" not in app_msg
    assert "duration_ms" not in app_msg

    # ACCESS_REQUEST is APP-only (stroom 1 and stroom 3 == "-")
    assert pub_buf.getvalue() == ""
    assert siem_buf.getvalue() == ""


def test_off_spec_extras_dropped_from_all_streams(
    streams: tuple[logging.Logger, io.StringIO, io.StringIO, io.StringIO],
) -> None:
    logger, pub_buf, app_buf, siem_buf = streams
    Log.event(
        logger,
        Log.CLIENT_ONBOARDED,
        "onboarded",
        oin="00000001000000000001",
        ura_number="12345678",
        scopes="read",
        bogus_field="should be dropped",
    )

    app_msg = _messages(app_buf)[0]
    siem_msg = _messages(siem_buf)[0]

    # APP keeps the spec'd fields; the off-spec `bogus_field` is dropped
    assert app_msg["oin"] == "00000001000000000001"
    assert app_msg["ura_number"] == "12345678"
    assert "bogus_field" not in app_msg

    # SIEM keeps its narrower subset; off-spec `bogus_field` and oin are dropped
    assert siem_msg["ura_number"] == "12345678"
    assert siem_msg["scopes"] == "read"
    assert "oin" not in siem_msg
    assert "bogus_field" not in siem_msg

    # CLIENT_ONBOARDED is not routed to PUB (stroom 1)
    assert pub_buf.getvalue() == ""
