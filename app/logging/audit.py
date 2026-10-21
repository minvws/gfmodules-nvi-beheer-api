from collections.abc import Mapping
from typing import Any
from uuid import UUID

from app.models.certificates import Certificate
from app.models.client import Client, ClientResolveRequest
from app.models.scopes import AuthorizationScope
from app.models.source import Source
from app.models.ura import UraNumber


def scope_names(scopes: list[AuthorizationScope] | None) -> list[str]:
    return sorted(str(scope) for scope in scopes or [])


def with_changes(before: Mapping[str, Any], after: Mapping[str, Any], *names: str) -> dict[str, Any]:
    changes = dict(after)
    for name in names:
        old, new = set(before[name]), set(after[name])
        changes[f"{name}_added"] = sorted(new - old)
        changes[f"{name}_removed"] = sorted(old - new)
    return changes


def organization_fields(id: UUID, ura_number: UraNumber, scopes: list[AuthorizationScope] | None) -> dict[str, Any]:
    return {"organization_id": str(id), "ura_number": str(ura_number), "scopes": scope_names(scopes)}


def client_fields(client: Client) -> dict[str, Any]:
    return {
        "organization_id": str(client.organization_id),
        "client_id": str(client.id),
        "scopes": scope_names(client.scopes),
        "certificate_ids": [str(c.id) for c in client.certificates or []],
        "source_ids": [s.source_id for s in client.sources or []],
    }


def certificate_fields(organization_id: UUID, certificate: Certificate) -> dict[str, Any]:
    return {
        "organization_id": str(organization_id),
        "certificate_id": str(certificate.id),
        "certificate_organization_identifier": str(certificate.organization_identifier),
        "domain": certificate.domain,
    }


def source_fields(source: Source) -> dict[str, Any]:
    return {"organization_id": str(source.organization_id), "source_id": source.source_id}


def resolve_request_fields(request: ClientResolveRequest) -> dict[str, Any]:
    return {
        "client_id": str(request.client_id),
        "ura_number": str(request.organization_external_id),
        "certificate_organization_identifier": str(request.certificate_organization_identifier),
        "source_id": request.source_id,
    }
