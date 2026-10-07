from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import DatabaseError, IntegrityError

from app.db.db import Database
from app.db.models.certificate import CertificateEntity
from app.db.models.client import ClientEntity
from app.db.models.organization import OrganizationEntity
from app.db.repository.contexts.organization_context import (
    OrganizationQueryContext,
)
from app.db.repository.organization import OrganizationRepository
from app.db.repository.scope import ScopeRepository
from app.models.organization import Organization, OrganizationCreate, OrganizationQueryParams, OrganizationUpdate
from app.services.certificate.client_certificate import ClientCertificateService
from app.services.exceptions import (
    ConflictError,
    EntityHasActiveMembersError,
    ForbidenOperationError,
    RecordNotFoundError,
)
from app.services.scopes.utils import ScopeUtils
from app.services.source.client_source import ClientSourceService


class OrganizationService:
    def __init__(self, db: Database) -> None:
        self.db = db

    def create_one(
        self,
        dto: OrganizationCreate,
    ) -> Organization:
        with self.db.get_db_session() as session:
            org_repo = session.get_repository(OrganizationRepository)
            if org_repo.exsits_by_external_id(dto.external_id):
                raise ConflictError(f"Organization external_id {dto.external_id.value} already exists")

            org_entity = OrganizationEntity(
                external_id=dto.external_id,
                name=dto.name,
            )
            if dto.scopes:
                scopes_repo = session.get_repository(ScopeRepository)
                app_scopes = scopes_repo.find_many()

                org_scopes = [s for s in app_scopes if s.name in dto.scopes]
                org_entity.scopes = org_scopes

            if dto.certificates:
                org_entity.certificates = [
                    CertificateEntity(organization_identifier=c.organization_identifier, domain=c.domain)
                    for c in dto.certificates
                ]

            if dto.sources:
                org_entity.sources = [s.into_entity() for s in dto.sources]

            if dto.clients:
                for client in dto.clients:
                    client_entitiy = ClientEntity(name=client.name, description=client.description)
                    if client.scopes:
                        ScopeUtils.assert_scopes_granted(org_entity, client.scopes)
                        client_scopes = ScopeUtils.make_client_scope_from_org(org_entity, client_entitiy, client.scopes)
                        client_entitiy.scopes = client_scopes

                    if client.certificates:
                        client_certs = ClientCertificateService.get_client_certs_from_org(
                            org_entity, client.certificates
                        )
                        client_entitiy.certificates = client_certs

                    if client.sources:
                        client_sources = ClientSourceService.get_client_sources_from_org(
                            org_entity, client.sources or []
                        )
                        client_entitiy.sources = client_sources

                    org_entity.clients.append(client_entitiy)

            org_repo.add_one(org_entity)
            new_org = org_repo.find_one(org_entity.id)
            if new_org is None:
                raise RuntimeError("Something went wrong")

            return Organization.from_entity(new_org)

    def get_one(self, id: UUID) -> Organization:
        with self.db.get_db_session() as session:
            repo = session.get_repository(OrganizationRepository)
            entity = repo.find_one(id)
            if entity is None:
                raise RecordNotFoundError(id)

            return Organization.from_entity(entity)

    def exists(self, id: UUID) -> bool:
        with self.db.get_db_session() as session:
            repo = session.get_repository(OrganizationRepository)
            return repo.exists(id)

    def get_many(
        self,
        params: OrganizationQueryParams,
    ) -> list[Organization]:
        with self.db.get_db_session() as session:
            repo = session.get_repository(OrganizationRepository)
            orgs = repo.find_many(
                ctx=params.into_organization_query_context(),
                include_deleted=params.include_deleted,
            )
            return [Organization.from_entity(org) for org in orgs]

    def update_one(self, id: UUID, dto: OrganizationUpdate) -> OrganizationUpdate:
        with self.db.get_db_session(commit=True) as session:
            org_repo = session.get_repository(OrganizationRepository)
            ctx = OrganizationQueryContext(id=id)
            org = org_repo.find(ctx)
            if not org:
                raise HTTPException(status_code=404)

            change_happened = OrganizationUpdate.from_entity(org) != dto
            if change_happened is False:
                return OrganizationUpdate.from_entity(org)

            if org.external_id != dto.external_id:
                org.external_id = dto.external_id
            if org.name != dto.name:
                org.name = dto.name

            # scope the dangerous transaction in a try catch block
            try:
                if dto.scopes:
                    scope_repo = session.get_repository(ScopeRepository)
                    app_scope = scope_repo.find_many()

                    org_scopes = [s for s in app_scope if s.name in dto.scopes]
                    org.scopes = org_scopes
                else:
                    org.scopes = []

                session.flush()
            except IntegrityError:
                raise ForbidenOperationError(f"Organization {org.id} has Clients using scopes marked for change")
                session.rollback()
            except DatabaseError:
                session.rollback()
                raise

            return OrganizationUpdate.from_entity(org)

    def delete_one(self, id: UUID) -> None:
        with self.db.get_db_session(commit=True) as session:
            repo = session.get_repository(OrganizationRepository)
            org = repo.find_one(id)
            if org is None:
                raise RecordNotFoundError(id)

            active_member = OrganizationService.validate_org_for_delete(org)
            if active_member:
                raise EntityHasActiveMembersError("Organization", active_member, id)

            org.deleted_at = datetime.now(UTC)

    @staticmethod
    def validate_org_for_delete(org: OrganizationEntity) -> str | None:
        valid_for_delete = True
        if org.clients:
            valid_for_delete = any(c.deleted_at is not None for c in org.clients)
            if valid_for_delete is False:
                return "Clients"

        if org.certificates:
            valid_for_delete = any(c.deleted_at is not None for c in org.certificates)
            if valid_for_delete is False:
                return "Certificates"

        if org.sources:
            valid_for_delete = any(s.deleted_at is not None for s in org.sources)
            if valid_for_delete is False:
                return "Sources"

        return None
