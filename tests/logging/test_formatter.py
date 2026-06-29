import json
import logging
import sys
from typing import Any, Iterator

import pytest

from app.logging.context import (
    client_trace_id_var,
    endpoint_var,
    ip_var,
    method_var,
    request_id_var,
)
from app.logging.filters import LoggingStreams
from app.logging.formatter import JsonFormatter, PlainTextFormatter


def _record(msg: str = "hello", level: int = logging.INFO, **extra: Any) -> logging.LogRecord:
    record = logging.LogRecord(
        name="app.test", level=level, pathname=__file__, lineno=1, msg=msg, args=(), exc_info=None
    )
    for k, v in extra.items():
        setattr(record, k, v)
    return record


def _exc_record() -> logging.LogRecord:
    try:
        raise ValueError("boom")
    except ValueError:
        record = _record()
        record.exc_info = sys.exc_info()
        return record


@pytest.fixture
def context_vars() -> Iterator[None]:
    t1 = request_id_var.set("req-1")
    t2 = ip_var.set("10.0.0.1")
    t3 = client_trace_id_var.set("trace-1")
    t4 = endpoint_var.set("/token")
    t5 = method_var.set("POST")
    try:
        yield
    finally:
        request_id_var.reset(t1)
        ip_var.reset(t2)
        client_trace_id_var.reset(t3)
        endpoint_var.reset(t4)
        method_var.reset(t5)


def _format_json(record: logging.LogRecord, include_traces: bool = True) -> Any:
    return json.loads(JsonFormatter(include_traces=include_traces).format(record))


def test_json_formatter_required_fields() -> None:
    out = _format_json(_record("hi", event_id="100600"))
    assert {"event_id", "timestamp", "level", "event_description", "source", "message"} <= out.keys()
    assert out["event_id"] == "100600"
    assert out["event_description"] == "hi"
    assert out["level"] == "INFO"


def test_json_formatter_strips_control_characters() -> None:
    assert _format_json(_record("a\x00b\x1fc"))["event_description"] == "abc"


def test_json_formatter_includes_exception_when_traces_on() -> None:
    out = _format_json(_exc_record(), include_traces=True)
    assert "ValueError" in str(out["message"]["exception"])


def test_json_formatter_omits_exception_when_traces_off() -> None:
    out = _format_json(_exc_record(), include_traces=False)
    assert "exception" not in out["message"]


def test_json_formatter_includes_stack_info_when_traces_on() -> None:
    record = _record()
    record.stack_info = "stack"
    assert "stack_info" in _format_json(record, include_traces=True)["message"]


def test_json_formatter_includes_extras(context_vars: None) -> None:
    out = _format_json(_record(custom="x", another=42))
    msg = out["message"]
    assert msg["custom"] == "x"
    assert msg["another"] == 42
    assert msg["request_id"] == "req-1"
    assert msg["ip"] == "10.0.0.1"
    assert msg["endpoint"] == "/token"
    assert msg["method"] == "POST"


def test_formatter_omits_unset_endpoint_and_method() -> None:
    # With no request context, endpoint/method default to "-" and must be dropped.
    out = _format_json(_record())
    assert "endpoint" not in out["message"]
    assert "method" not in out["message"]


def test_plaintext_formatter_includes_basic_fields(context_vars: None) -> None:
    out = PlainTextFormatter().format(_record("hello", event_id="100600", custom="x"))
    assert "INFO" in out
    assert "[100600]" in out
    assert "hello" in out
    assert "custom=x" in out
    assert "request_id=req-1" in out


def test_plaintext_formatter_appends_exception() -> None:
    out = PlainTextFormatter().format(_exc_record())
    assert "ValueError" in out


# --- per-field stream routing (stroom 2 == APP, stroom 3 == SIEM) ---

# Mirrors Log.CLIENT_OFFBOARDED: oin and reason belong to APP only, not SIEM.
_OFFBOARD_FIELD_STREAMS = {
    LoggingStreams.APP: ("oin", "ura_number", "deactivated_by", "reason"),
    LoggingStreams.SIEM: ("ura_number", "deactivated_by"),
}


def _routed_record() -> logging.LogRecord:
    return _record(
        event_id="100608",
        field_streams=_OFFBOARD_FIELD_STREAMS,
        oin="00000001000000000001",
        ura_number="12345678",
        deactivated_by="admin",
        reason="contract ended",
    )


def test_routing_siem_drops_app_only_fields(context_vars: None) -> None:
    msg = json.loads(JsonFormatter(stream=LoggingStreams.SIEM).format(_routed_record()))["message"]
    # SIEM allow-list keeps these
    assert msg["ura_number"] == "12345678"
    assert msg["deactivated_by"] == "admin"
    # APP-only fields are dropped from the SIEM stream
    assert "oin" not in msg
    assert "reason" not in msg
    # context fields not in the allow-list are dropped too
    assert "endpoint" not in msg
    assert "method" not in msg
    # correlation metadata is always retained
    assert msg["request_id"] == "req-1"
    assert msg["ip"] == "10.0.0.1"


def test_routing_app_keeps_app_fields(context_vars: None) -> None:
    msg = json.loads(JsonFormatter(stream=LoggingStreams.APP).format(_routed_record()))["message"]
    assert msg["oin"] == "00000001000000000001"
    assert msg["ura_number"] == "12345678"
    assert msg["deactivated_by"] == "admin"
    assert msg["reason"] == "contract ended"


def test_routing_unbound_formatter_keeps_everything(context_vars: None) -> None:
    # No stream binding (console/debug) => no filtering.
    msg = json.loads(JsonFormatter(stream=None).format(_routed_record()))["message"]
    assert msg["oin"] == "00000001000000000001"
    assert msg["reason"] == "contract ended"
    assert msg["method"] == "POST"


def test_routing_ignored_when_event_has_no_field_map(context_vars: None) -> None:
    # Event without field_streams => stream-bound formatter still keeps all fields.
    record = _record(event_id="100601", custom="x")
    msg = json.loads(JsonFormatter(stream=LoggingStreams.SIEM).format(record))["message"]
    assert msg["custom"] == "x"
    assert msg["method"] == "POST"


def test_routing_applies_to_plaintext(context_vars: None) -> None:
    out = PlainTextFormatter(stream=LoggingStreams.SIEM).format(_routed_record())
    assert "ura_number=12345678" in out
    assert "reason" not in out
