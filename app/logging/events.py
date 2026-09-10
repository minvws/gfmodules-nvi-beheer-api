import logging

from gfmodules.logging import DefaultEventCatalogue, LogEvent, LoggingStreams

_APP = LoggingStreams.APP
_SIEM = LoggingStreams.SIEM

_Base = DefaultEventCatalogue


class Log(_Base):
    SYS_APP_STARTED = _Base.SYS_APP_STARTED.with_id("100601")  # NVI-SYS-001
    SYS_APP_STOPPED = _Base.SYS_APP_STOPPED.with_id("100602")  # NVI-SYS-002
    SYS_APP_CRASHED = _Base.SYS_APP_CRASHED.with_id("100602")  # NVI-SYS-002
    SYS_UNHANDLED_EXCEPTION = _Base.SYS_UNHANDLED_EXCEPTION.with_id("100604")  # NVI-SYS-004
    SYS_MISSING_CORRELATION_ID = _Base.SYS_MISSING_CORRELATION_ID.with_id("100606")  # NVI-SYS-006

    HEALTH_UNHEALTHY = LogEvent(  # NVI-HEALTH-001
        "100600",
        logging.ERROR,
        (_APP, _SIEM),
        {_APP: ("component", "status", "error_detail"), _SIEM: ("component", "status")},
    )
    DB_CONNECTION_FAILED = LogEvent(  # NVI-SYS-003
        "100603",
        logging.ERROR,
        (_APP, _SIEM),
        {_APP: ("error_type", "retry_attempt", "backoff_seconds"), _SIEM: ("error_type",)},
    )
    DB_SCHEMA_ERROR = LogEvent(  # NVI-SYS-005
        "100605",
        logging.ERROR,
        (_APP,),
        {
            _APP: ("exception_type", "table", "column", "value_length", "column_limit"),
        },
    )

    CLIENT_ONBOARDED = LogEvent(  # NVI-OB-001
        "100607",
        logging.INFO,
        (_APP, _SIEM),
        {_APP: ("oin", "ura_number", "source_identifier", "approved_by", "scopes"), _SIEM: ("ura_number", "scopes")},
    )
    CLIENT_OFFBOARDED = LogEvent(  # NVI-OB-002
        "100608",
        logging.WARNING,
        (_APP, _SIEM),
        {_APP: ("oin", "ura_number", "deactivated_by", "reason"), _SIEM: ("ura_number", "deactivated_by")},
    )
    CREDENTIAL_COUPLED = LogEvent(  # NVI-OB-003
        "100609",
        logging.INFO,
        (_APP, _SIEM),
        {
            _APP: ("ura_number", "old_cert_thumbprint_prefix", "new_cert_thumbprint_prefix", "changed_by"),
            _SIEM: ("ura_number",),
        },
    )

    access_event_id = {
        ("POST", "/organizations"): "100700",
        ("PUT", "/organizations/{id}"): "100701",
        ("DELETE", "/organizations/{id}"): "100702",
        ("POST", "/organizations/{organization_id}/clients"): "100703",
        ("PUT", "/organizations/{organization_id}/clients/{id}"): "100704",
        ("DELETE", "/organizations/{organization_id}/clients/{id}"): "100705",
    }
