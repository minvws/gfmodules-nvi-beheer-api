import logging
from typing import ClassVar

from gfmodules.logging import ContextField, DefaultEventCatalogue, LogEvent, LoggingStreams
from gfmodules.logging.context import sanitize_free_text

_APP = LoggingStreams.APP
_SIEM = LoggingStreams.SIEM

_Base = DefaultEventCatalogue

ACTOR = ContextField(name="actor_cn", header="x-gf-act-cn", sanitizer=sanitize_free_text)


def _app_and_siem(
    event_id: str,
    fields: tuple[str, ...],
    app_only: tuple[str, ...] = (),
    level: int = logging.INFO,
) -> LogEvent:
    siem = (ACTOR.name, *fields)
    return LogEvent(event_id, level, (_APP, _SIEM), {_APP: (*siem, *app_only), _SIEM: siem})


def _app_only(event_id: str, fields: tuple[str, ...], level: int = logging.INFO) -> LogEvent:
    return LogEvent(event_id, level, (_APP,), {_APP: (ACTOR.name, *fields)})


_ORGANIZATION = ("organization_id", "ura_number", "scopes")
_CLIENT = ("organization_id", "client_id", "scopes", "certificate_ids", "source_ids")
_CERTIFICATE = ("organization_id", "certificate_id", "certificate_organization_identifier")
_CLIENT_CERTIFICATE = (*_CERTIFICATE, "client_id")
_SOURCE = ("organization_id", "source_id")
_CLIENT_SOURCE = (*_SOURCE, "client_id")
_RESOLVE = ("client_id", "ura_number", "certificate_organization_identifier")
_REFUSAL = ("error_reason", "status_code")


class Log(_Base):
    SYS_APP_STARTED = _Base.SYS_APP_STARTED.with_id("100601")
    SYS_APP_STOPPED = _Base.SYS_APP_STOPPED.with_id("100602")
    SYS_APP_CRASHED = _Base.SYS_APP_CRASHED.with_id("100602")
    SYS_UNHANDLED_EXCEPTION = _Base.SYS_UNHANDLED_EXCEPTION.with_id("100604").add_fields(
        {_APP: (ACTOR.name,), _SIEM: (ACTOR.name,)}
    )
    SYS_MISSING_CORRELATION_ID = _Base.SYS_MISSING_CORRELATION_ID.with_id("100606")
    ACCESS_REQUEST = _Base.ACCESS_REQUEST.add_fields({_APP: (ACTOR.name,)})

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

    ORGANIZATION_CREATED = _app_and_siem("100607", _ORGANIZATION)
    ORGANIZATION_UPDATED = _app_and_siem("100608", (*_ORGANIZATION, "scopes_added", "scopes_removed"))
    ORGANIZATION_DELETED = _app_and_siem("100609", _ORGANIZATION)
    CLIENT_CREATED = _app_and_siem("100610", _CLIENT)
    CLIENT_UPDATED = _app_and_siem(
        "100611",
        (
            *_CLIENT,
            "scopes_added",
            "scopes_removed",
            "certificate_ids_added",
            "certificate_ids_removed",
            "source_ids_added",
            "source_ids_removed",
        ),
    )
    CLIENT_DELETED = _app_and_siem("100612", _CLIENT)
    CERTIFICATE_CREATED = _app_and_siem("100613", _CERTIFICATE, app_only=("domain",))
    CERTIFICATE_UPDATED = _app_and_siem("100614", _CERTIFICATE, app_only=("domain",))
    CERTIFICATE_DELETED = _app_and_siem("100615", _CERTIFICATE, app_only=("domain",))
    CLIENT_CERTIFICATE_ASSIGNED = _app_and_siem("100616", _CLIENT_CERTIFICATE, app_only=("domain",))
    CLIENT_CERTIFICATE_UNASSIGNED = _app_and_siem("100617", _CLIENT_CERTIFICATE, app_only=("domain",))
    SOURCE_CREATED = _app_and_siem("100618", _SOURCE)
    SOURCE_UPDATED = _app_and_siem("100619", _SOURCE)
    SOURCE_DELETED = _app_and_siem("100620", _SOURCE)
    CLIENT_SOURCE_ASSIGNED = _app_and_siem("100621", _CLIENT_SOURCE)
    CLIENT_SOURCE_UNASSIGNED = _app_and_siem("100622", _CLIENT_SOURCE)
    CLIENT_RESOLVED = _app_only("100623", (*_RESOLVE, "matched_domain", "source_id", "scopes"))
    CLIENT_RESOLVE_DENIED = _app_and_siem(
        "100625",
        (*_RESOLVE, "error_reason"),
        app_only=("certificate_domains", "source_id"),
        level=logging.WARNING,
    )
    REQUEST_REFUSED = _app_only("100624", (*_REFUSAL, "validation_errors"), level=logging.WARNING)
    REQUEST_FORBIDDEN = _app_and_siem("100627", _REFUSAL, level=logging.WARNING)

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
