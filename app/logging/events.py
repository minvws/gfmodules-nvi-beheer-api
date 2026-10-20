import logging
from typing import ClassVar

from gfmodules.logging import DefaultEventCatalogue, LogEvent, LoggingStreams

_APP = LoggingStreams.APP
_SIEM = LoggingStreams.SIEM

_Base = DefaultEventCatalogue

_ORGANIZATION_FIELDS = {
    _APP: ("organization_id", "ura_number", "scopes"),
    _SIEM: ("organization_id", "ura_number", "scopes"),
}
_CLIENT_FIELDS = {
    _APP: ("organization_id", "client_id", "scopes", "certificate_ids", "source_ids"),
    _SIEM: ("organization_id", "client_id", "scopes"),
}
_CERTIFICATE_FIELDS = {
    _APP: ("organization_id", "certificate_id", "certificate_organization_identifier", "domain"),
    _SIEM: ("organization_id", "certificate_id", "certificate_organization_identifier"),
}
_CLIENT_CERTIFICATE_FIELDS = {
    _APP: ("organization_id", "client_id", "certificate_id", "certificate_organization_identifier", "domain"),
    _SIEM: ("organization_id", "client_id", "certificate_id", "certificate_organization_identifier"),
}
_SOURCE_FIELDS = {
    _APP: ("organization_id", "source_id"),
    _SIEM: ("organization_id", "source_id"),
}
_CLIENT_SOURCE_FIELDS = {
    _APP: ("organization_id", "client_id", "source_id"),
    _SIEM: ("organization_id", "client_id", "source_id"),
}


class Log(_Base):
    SYS_APP_STARTED = _Base.SYS_APP_STARTED.with_id("100601")
    SYS_APP_STOPPED = _Base.SYS_APP_STOPPED.with_id("100602")
    SYS_APP_CRASHED = _Base.SYS_APP_CRASHED.with_id("100602")
    SYS_UNHANDLED_EXCEPTION = _Base.SYS_UNHANDLED_EXCEPTION.with_id("100604")
    SYS_MISSING_CORRELATION_ID = _Base.SYS_MISSING_CORRELATION_ID.with_id("100606")

    HEALTH_UNHEALTHY = LogEvent(
        "100600",
        logging.ERROR,
        (_APP, _SIEM),
        {_APP: ("component", "status", "error_detail"), _SIEM: ("component", "status")},
    )
    DB_CONNECTION_FAILED = LogEvent(
        "100603",
        logging.ERROR,
        (_APP, _SIEM),
        {_APP: ("error_type", "retry_attempt", "backoff_seconds"), _SIEM: ("error_type",)},
    )
    DB_SCHEMA_ERROR = LogEvent(
        "100605",
        logging.ERROR,
        (_APP,),
        {
            _APP: ("exception_type", "table", "column", "value_length", "column_limit"),
        },
    )
    DB_OPERATION_FAILED = LogEvent(
        "100626",
        logging.WARNING,
        (_APP,),
        {_APP: ("exception_type", "table", "constraint")},
    )

    ORGANIZATION_CREATED = LogEvent("100607", logging.INFO, (_APP, _SIEM), _ORGANIZATION_FIELDS)
    ORGANIZATION_UPDATED = LogEvent("100608", logging.INFO, (_APP, _SIEM), _ORGANIZATION_FIELDS)
    ORGANIZATION_DELETED = LogEvent("100609", logging.INFO, (_APP, _SIEM), _ORGANIZATION_FIELDS)
    CLIENT_CREATED = LogEvent("100610", logging.INFO, (_APP, _SIEM), _CLIENT_FIELDS)
    CLIENT_UPDATED = LogEvent("100611", logging.INFO, (_APP, _SIEM), _CLIENT_FIELDS)
    CLIENT_DELETED = LogEvent("100612", logging.INFO, (_APP, _SIEM), _CLIENT_FIELDS)
    CERTIFICATE_CREATED = LogEvent("100613", logging.INFO, (_APP, _SIEM), _CERTIFICATE_FIELDS)
    CERTIFICATE_UPDATED = LogEvent("100614", logging.INFO, (_APP, _SIEM), _CERTIFICATE_FIELDS)
    CERTIFICATE_DELETED = LogEvent("100615", logging.INFO, (_APP, _SIEM), _CERTIFICATE_FIELDS)
    CLIENT_CERTIFICATE_ASSIGNED = LogEvent("100616", logging.INFO, (_APP, _SIEM), _CLIENT_CERTIFICATE_FIELDS)
    CLIENT_CERTIFICATE_UNASSIGNED = LogEvent("100617", logging.INFO, (_APP, _SIEM), _CLIENT_CERTIFICATE_FIELDS)
    SOURCE_CREATED = LogEvent("100618", logging.INFO, (_APP, _SIEM), _SOURCE_FIELDS)
    SOURCE_UPDATED = LogEvent("100619", logging.INFO, (_APP, _SIEM), _SOURCE_FIELDS)
    SOURCE_DELETED = LogEvent("100620", logging.INFO, (_APP, _SIEM), _SOURCE_FIELDS)
    CLIENT_SOURCE_ASSIGNED = LogEvent("100621", logging.INFO, (_APP, _SIEM), _CLIENT_SOURCE_FIELDS)
    CLIENT_SOURCE_UNASSIGNED = LogEvent("100622", logging.INFO, (_APP, _SIEM), _CLIENT_SOURCE_FIELDS)
    CLIENT_RESOLVED = LogEvent(
        "100623",
        logging.INFO,
        (_APP, _SIEM),
        {
            _APP: (
                "client_id",
                "ura_number",
                "certificate_organization_identifier",
                "matched_domain",
                "source_id",
                "scopes",
            ),
            _SIEM: ("client_id", "ura_number", "certificate_organization_identifier", "scopes"),
        },
    )
    REQUEST_REFUSED = LogEvent(
        "100624",
        logging.WARNING,
        (_APP, _SIEM),
        {_APP: ("error_type", "status_code", "validation_errors"), _SIEM: ("error_type", "status_code")},
    )
    CLIENT_RESOLVE_DENIED = LogEvent(
        "100625",
        logging.WARNING,
        (_APP, _SIEM),
        {
            _APP: (
                "client_id",
                "ura_number",
                "certificate_organization_identifier",
                "certificate_domains",
                "source_id",
                "error_reason",
            ),
            _SIEM: ("client_id", "ura_number", "certificate_organization_identifier", "error_reason"),
        },
    )

    access_event_id: ClassVar = {
        ("POST", "/organizations"): "100700",
        ("PUT", "/organizations/{id}"): "100701",
        ("DELETE", "/organizations/{id}"): "100702",
        ("POST", "/organizations/{organization_id}/clients"): "100703",
        ("PUT", "/organizations/{organization_id}/clients/{id}"): "100704",
        ("DELETE", "/organizations/{organization_id}/clients/{id}"): "100705",
        ("POST", "/organizations/{organization_id}/certificate"): "100706",
        ("PUT", "/organizations/{organization_id}/certificate/{id}"): "100707",
        ("DELETE", "/organizations/{organization_id}/certificate/{id}"): "100708",
        ("POST", "/organizations/{organization_id}/clients/{client_id}/certificate/{id}"): "100709",
        ("DELETE", "/organizations/{organization_id}/clients/{client_id}/certificate/{id}"): "100710",
        ("POST", "/organizations/{organization_id}/source"): "100711",
        ("PUT", "/organizations/{organization_id}/source/{id}"): "100712",
        ("DELETE", "/organizations/{organization_id}/source/{id}"): "100713",
        ("POST", "/organizations/{organization_id}/clients/{client_id}/sources/{id}"): "100714",
        ("DELETE", "/organizations/{organization_id}/clients/{client_id}/sources/{id}"): "100715",
        ("POST", "/clients/resolve"): "100716",
    }
