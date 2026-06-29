import json
import logging

import pytest

from app.logging.events import Log, NVIEvent
from app.logging.filters import LoggingStreams
from app.logging.formatter import JsonFormatter


def test_log_event_attaches_event_id_and_streams(caplog: pytest.LogCaptureFixture) -> None:
    logger = logging.getLogger("app.test_events")
    logger.setLevel(logging.DEBUG)
    with caplog.at_level(logging.DEBUG, logger="app.test_events"):
        Log.event(logger, Log.SYS_APP_STARTED, "started", version="1.0")

    record = caplog.records[-1]
    assert record.event_id == Log.SYS_APP_STARTED.event_id  # type: ignore
    assert LoggingStreams.APP in record.stream  # type: ignore
    assert record.version == "1.0"  # type: ignore
    assert record.levelno == logging.INFO


@pytest.mark.parametrize(
    "event,expected_level",
    [
        (Log.SYS_APP_STARTED, logging.INFO),
        (Log.HEALTH_UNHEALTHY, logging.ERROR),
        (Log.SYS_UNHANDLED_EXCEPTION, logging.ERROR),
    ],
)
def test_log_event_uses_event_level(caplog: pytest.LogCaptureFixture, event: object, expected_level: int) -> None:
    logger = logging.getLogger("app.test_events_levels")
    logger.setLevel(logging.DEBUG)
    with caplog.at_level(logging.DEBUG, logger="app.test_events_levels"):
        Log.event(logger, event, "msg")  # type: ignore[arg-type]
    assert caplog.records[-1].levelno == expected_level


def test_log_event_attaches_field_streams_for_routed_events(caplog: pytest.LogCaptureFixture) -> None:
    logger = logging.getLogger("app.test_events_routing")
    logger.setLevel(logging.DEBUG)
    with caplog.at_level(logging.DEBUG, logger="app.test_events_routing"):
        Log.event(logger, Log.CLIENT_ONBOARDED, "onboarded", ura_number="12345678")

    record = caplog.records[-1]
    field_streams = record.field_streams  # type: ignore[attr-defined]
    assert field_streams[LoggingStreams.APP] == ("oin", "ura_number", "source_identifier", "approved_by", "scopes")
    assert field_streams[LoggingStreams.SIEM] == ("ura_number", "scopes")
    assert LoggingStreams.PUBLIC_INSPECT not in field_streams


def test_log_event_omits_field_streams_for_plain_events(caplog: pytest.LogCaptureFixture) -> None:
    plain_event = NVIEvent("000000", logging.INFO, (LoggingStreams.APP,))
    logger = logging.getLogger("app.test_events_plain")
    logger.setLevel(logging.DEBUG)
    with caplog.at_level(logging.DEBUG, logger="app.test_events_plain"):
        Log.event(logger, plain_event, "started")

    assert not hasattr(caplog.records[-1], "field_streams")


def test_unhandled_exception_type_survives_app_routing() -> None:
    record = logging.LogRecord(
        name="app", level=logging.ERROR, pathname=__file__, lineno=1, msg="fail", args=(), exc_info=None
    )
    record.event_id = Log.SYS_UNHANDLED_EXCEPTION.event_id
    record.field_streams = Log.SYS_UNHANDLED_EXCEPTION.fields
    record.exception_type = "RuntimeError"

    message = json.loads(JsonFormatter(stream=LoggingStreams.APP).format(record))["message"]
    assert message["exception_type"] == "RuntimeError"


def test_log_event_includes_exc_info(caplog: pytest.LogCaptureFixture) -> None:
    logger = logging.getLogger("app.test_events_exc")
    logger.setLevel(logging.DEBUG)
    try:
        raise ValueError("boom")
    except ValueError as e:
        with caplog.at_level(logging.DEBUG, logger="app.test_events_exc"):
            Log.event(logger, Log.SYS_UNHANDLED_EXCEPTION, "fail", exc_info=e)

    assert caplog.records[-1].exc_info is not None
