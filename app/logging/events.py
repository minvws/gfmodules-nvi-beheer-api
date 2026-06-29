import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from app.logging.filters import LoggingStreams

_APP = LoggingStreams.APP
_SIEM = LoggingStreams.SIEM


@dataclass(frozen=True)
class NVIEvent:
    event_id: str
    level: int
    streams: tuple[LoggingStreams, ...]
    # Per-stream allow-list of field names. PUB == "stroom 1", APP == "stroom 2", SIEM == "stroom 3".
    # When empty, no per-field routing is applied and every field is sent to all streams in streams
    fields: Mapping[LoggingStreams, tuple[str, ...]] = field(default_factory=dict)


class Log:
    # System / Health (NVI-SYS / NVI-HEALTH)
    HEALTH_UNHEALTHY = NVIEvent(  # NVI-HEALTH-001
        "100600",
        logging.ERROR,
        (_APP, _SIEM),
        {_APP: ("component", "status", "error_detail"), _SIEM: ("component", "status")},
    )
    SYS_APP_STARTED = NVIEvent(  # NVI-SYS-001
        "100601", logging.INFO, (_APP,), {_APP: ("version", "config_path")}
    )
    SYS_APP_STOPPED = NVIEvent(  # NVI-SYS-002
        "100602",
        logging.INFO,
        (_APP, _SIEM),
        {_APP: ("shutdown_reason", "last_exception_type"), _SIEM: ("shutdown_reason",)},  # graceful/signal
    )
    SYS_APP_CRASHED = NVIEvent(  # NVI-SYS-002
        "100602",
        logging.CRITICAL,
        (_APP, _SIEM),
        {_APP: ("shutdown_reason", "last_exception_type"), _SIEM: ("shutdown_reason",)},  # crash
    )
    DB_CONNECTION_FAILED = NVIEvent(  # NVI-SYS-003
        "100603",
        logging.ERROR,
        (_APP, _SIEM),
        {_APP: ("error_type", "retry_attempt", "backoff_seconds"), _SIEM: ("error_type",)},
    )
    SYS_UNHANDLED_EXCEPTION = NVIEvent(  # NVI-SYS-004
        "100604",
        logging.ERROR,
        (_APP, _SIEM),
        {_APP: ("exception_type", "endpoint", "method"), _SIEM: ("exception_type", "endpoint", "method")},
    )
    DB_SCHEMA_ERROR = NVIEvent(  # NVI-SYS-005
        "100605",
        logging.ERROR,
        (_APP,),
        {
            _APP: ("exception_type", "table", "column", "value_length", "column_limit"),
        },
    )

    ACCESS_REQUEST = NVIEvent(  # NVI-AUTH-101
        "094500",
        logging.INFO,
        (_APP,),
        {_APP: ("endpoint", "method")},
    )

    CLIENT_ONBOARDED = NVIEvent(  # NVI-OB-001
        "100607",
        logging.INFO,
        (_APP, _SIEM),
        {_APP: ("oin", "ura_number", "source_identifier", "approved_by", "scopes"), _SIEM: ("ura_number", "scopes")},
    )
    CLIENT_OFFBOARDED = NVIEvent(  # NVI-OB-002
        "100608",
        logging.WARNING,
        (_APP, _SIEM),
        {_APP: ("oin", "ura_number", "deactivated_by", "reason"), _SIEM: ("ura_number", "deactivated_by")},
    )
    # Event below is not logged since code for this logic is not implemented yet. It is added here for future use.
    CREDENTIAL_COUPLED = NVIEvent(  # NVI-OB-003
        "100609",
        logging.INFO,
        (_APP, _SIEM),
        {
            _APP: ("ura_number", "old_cert_thumbprint_prefix", "new_cert_thumbprint_prefix", "changed_by"),
            _SIEM: ("ura_number",),
        },
    )

    @staticmethod
    def event(
        logger: logging.Logger,
        event: NVIEvent,
        message: str,
        *,
        exc_info: Any = None,
        **fields: Any,
    ) -> None:
        extra: dict[str, Any] = {
            "event_id": event.event_id,
            "stream": list(event.streams),
        }
        if event.fields:
            extra["field_streams"] = event.fields
        extra.update(fields)
        logger.log(event.level, message, extra=extra, exc_info=exc_info)
