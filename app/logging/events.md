# Log events

<!-- markdownlint-disable MD013 -->

Generated from `app.logging.events:Log` by `gfmodules.logging.event_overview`.
Do not edit by hand.

Each stream lists the events that reach it and the fields they carry there besides the context fields.
*any* means the event has no allow-list, so every field it is logged with reaches the stream.
*none* means the event carries only the context fields there.

## Context fields

Every event carries these on every stream, whenever the request context holds a value for them.

- `request_id`
- `ip`
- `user_agent`
- `client_trace_id`
- `correlation_id`
- `endpoint`
- `method`
- `scope`

## Stream `app`

| Event | Id | Level | Fields |
| --- | --- | --- | --- |
| `SYS_APP_STARTED` | 100601 | INFO | `version`, `config_path` |
| `SYS_APP_STOPPED` | 100602 | INFO | `shutdown_reason`, `last_exception_type` |
| `SYS_APP_CRASHED` | 100602 | CRITICAL | `shutdown_reason`, `last_exception_type` |
| `SYS_UNHANDLED_EXCEPTION` | 100604 | ERROR | `exception_type`, `endpoint`, `method`, `actor_cn` |
| `SYS_MISSING_CORRELATION_ID` | 100606 | ERROR | `endpoint`, `method` |
| `ACCESS_REQUEST` | 100 | INFO | `endpoint`, `method`, `status_code`, `duration_ms`, `body`, `body_truncated`, `actor_cn` |
| `HEALTH_UNHEALTHY` | 100600 | ERROR | `component`, `status`, `error_detail` |
| `DB_CONNECTION_FAILED` | 100603 | ERROR | `error_type`, `retry_attempt`, `backoff_seconds` |
| `DB_SCHEMA_ERROR` | 100605 | ERROR | `exception_type`, `table`, `column`, `value_length`, `column_limit` |
| `DB_OPERATION_FAILED` | 100626 | WARNING | `exception_type`, `table`, `constraint` |
| `ORGANIZATION_CREATED` | 100607 | INFO | `actor_cn`, `organization_id`, `ura_number`, `scopes` |
| `ORGANIZATION_UPDATED` | 100608 | INFO | `actor_cn`, `organization_id`, `ura_number`, `scopes`, `scopes_added`, `scopes_removed` |
| `ORGANIZATION_DELETED` | 100609 | INFO | `actor_cn`, `organization_id`, `ura_number`, `scopes` |
| `CLIENT_CREATED` | 100610 | INFO | `actor_cn`, `organization_id`, `client_id`, `scopes`, `certificate_ids`, `source_ids` |
| `CLIENT_UPDATED` | 100611 | INFO | `actor_cn`, `organization_id`, `client_id`, `scopes`, `certificate_ids`, `source_ids`, `scopes_added`, `scopes_removed`, `certificate_ids_added`, `certificate_ids_removed`, `source_ids_added`, `source_ids_removed` |
| `CLIENT_DELETED` | 100612 | INFO | `actor_cn`, `organization_id`, `client_id`, `scopes`, `certificate_ids`, `source_ids` |
| `CERTIFICATE_CREATED` | 100613 | INFO | `actor_cn`, `organization_id`, `certificate_id`, `certificate_organization_identifier`, `domain` |
| `CERTIFICATE_UPDATED` | 100614 | INFO | `actor_cn`, `organization_id`, `certificate_id`, `certificate_organization_identifier`, `domain` |
| `CERTIFICATE_DELETED` | 100615 | INFO | `actor_cn`, `organization_id`, `certificate_id`, `certificate_organization_identifier`, `domain` |
| `CLIENT_CERTIFICATE_ASSIGNED` | 100616 | INFO | `actor_cn`, `organization_id`, `certificate_id`, `certificate_organization_identifier`, `client_id`, `domain` |
| `CLIENT_CERTIFICATE_UNASSIGNED` | 100617 | INFO | `actor_cn`, `organization_id`, `certificate_id`, `certificate_organization_identifier`, `client_id`, `domain` |
| `SOURCE_CREATED` | 100618 | INFO | `actor_cn`, `organization_id`, `source_id` |
| `SOURCE_UPDATED` | 100619 | INFO | `actor_cn`, `organization_id`, `source_id` |
| `SOURCE_DELETED` | 100620 | INFO | `actor_cn`, `organization_id`, `source_id` |
| `CLIENT_SOURCE_ASSIGNED` | 100621 | INFO | `actor_cn`, `organization_id`, `source_id`, `client_id` |
| `CLIENT_SOURCE_UNASSIGNED` | 100622 | INFO | `actor_cn`, `organization_id`, `source_id`, `client_id` |
| `CLIENT_RESOLVED` | 100623 | INFO | `actor_cn`, `client_id`, `ura_number`, `certificate_organization_identifier`, `matched_domain`, `source_id`, `scopes` |
| `CLIENT_RESOLVE_DENIED` | 100625 | WARNING | `actor_cn`, `client_id`, `ura_number`, `certificate_organization_identifier`, `error_reason`, `certificate_domains`, `source_id` |
| `REQUEST_REFUSED` | 100624 | WARNING | `actor_cn`, `error_reason`, `status_code`, `validation_errors` |
| `REQUEST_FORBIDDEN` | 100627 | WARNING | `actor_cn`, `error_reason`, `status_code` |

## Stream `siem`

| Event | Id | Level | Fields |
| --- | --- | --- | --- |
| `SYS_APP_STOPPED` | 100602 | INFO | `shutdown_reason` |
| `SYS_APP_CRASHED` | 100602 | CRITICAL | `shutdown_reason` |
| `SYS_UNHANDLED_EXCEPTION` | 100604 | ERROR | `exception_type`, `endpoint`, `method`, `actor_cn` |
| `HEALTH_UNHEALTHY` | 100600 | ERROR | `component`, `status` |
| `DB_CONNECTION_FAILED` | 100603 | ERROR | `error_type` |
| `ORGANIZATION_CREATED` | 100607 | INFO | `actor_cn`, `organization_id`, `ura_number`, `scopes` |
| `ORGANIZATION_UPDATED` | 100608 | INFO | `actor_cn`, `organization_id`, `ura_number`, `scopes`, `scopes_added`, `scopes_removed` |
| `ORGANIZATION_DELETED` | 100609 | INFO | `actor_cn`, `organization_id`, `ura_number`, `scopes` |
| `CLIENT_CREATED` | 100610 | INFO | `actor_cn`, `organization_id`, `client_id`, `scopes`, `certificate_ids`, `source_ids` |
| `CLIENT_UPDATED` | 100611 | INFO | `actor_cn`, `organization_id`, `client_id`, `scopes`, `certificate_ids`, `source_ids`, `scopes_added`, `scopes_removed`, `certificate_ids_added`, `certificate_ids_removed`, `source_ids_added`, `source_ids_removed` |
| `CLIENT_DELETED` | 100612 | INFO | `actor_cn`, `organization_id`, `client_id`, `scopes`, `certificate_ids`, `source_ids` |
| `CERTIFICATE_CREATED` | 100613 | INFO | `actor_cn`, `organization_id`, `certificate_id`, `certificate_organization_identifier` |
| `CERTIFICATE_UPDATED` | 100614 | INFO | `actor_cn`, `organization_id`, `certificate_id`, `certificate_organization_identifier` |
| `CERTIFICATE_DELETED` | 100615 | INFO | `actor_cn`, `organization_id`, `certificate_id`, `certificate_organization_identifier` |
| `CLIENT_CERTIFICATE_ASSIGNED` | 100616 | INFO | `actor_cn`, `organization_id`, `certificate_id`, `certificate_organization_identifier`, `client_id` |
| `CLIENT_CERTIFICATE_UNASSIGNED` | 100617 | INFO | `actor_cn`, `organization_id`, `certificate_id`, `certificate_organization_identifier`, `client_id` |
| `SOURCE_CREATED` | 100618 | INFO | `actor_cn`, `organization_id`, `source_id` |
| `SOURCE_UPDATED` | 100619 | INFO | `actor_cn`, `organization_id`, `source_id` |
| `SOURCE_DELETED` | 100620 | INFO | `actor_cn`, `organization_id`, `source_id` |
| `CLIENT_SOURCE_ASSIGNED` | 100621 | INFO | `actor_cn`, `organization_id`, `source_id`, `client_id` |
| `CLIENT_SOURCE_UNASSIGNED` | 100622 | INFO | `actor_cn`, `organization_id`, `source_id`, `client_id` |
| `CLIENT_RESOLVE_DENIED` | 100625 | WARNING | `actor_cn`, `client_id`, `ura_number`, `certificate_organization_identifier`, `error_reason` |
| `REQUEST_FORBIDDEN` | 100627 | WARNING | `actor_cn`, `error_reason`, `status_code` |

## Access event ids per route

`ACCESS_REQUEST` carries these ids instead of its own on these routes.

| Method | Route | Id |
| --- | --- | --- |
| POST | `/organizations` | 100700 |
| PUT | `/organizations/{id}` | 100701 |
| DELETE | `/organizations/{id}` | 100702 |
| POST | `/organizations/{organization_id}/clients` | 100703 |
| PUT | `/organizations/{organization_id}/clients/{id}` | 100704 |
| DELETE | `/organizations/{organization_id}/clients/{id}` | 100705 |
| POST | `/organizations/{organization_id}/certificate` | 100706 |
| PUT | `/organizations/{organization_id}/certificate/{id}` | 100707 |
| DELETE | `/organizations/{organization_id}/certificate/{id}` | 100708 |
| POST | `/organizations/{organization_id}/clients/{client_id}/certificate/{id}` | 100709 |
| DELETE | `/organizations/{organization_id}/clients/{client_id}/certificate/{id}` | 100710 |
| POST | `/organizations/{organization_id}/source` | 100711 |
| PUT | `/organizations/{organization_id}/source/{id}` | 100712 |
| DELETE | `/organizations/{organization_id}/source/{id}` | 100713 |
| POST | `/organizations/{organization_id}/clients/{client_id}/sources/{id}` | 100714 |
| DELETE | `/organizations/{organization_id}/clients/{client_id}/sources/{id}` | 100715 |
| POST | `/clients/resolve` | 100716 |
