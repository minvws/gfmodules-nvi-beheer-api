from datetime import datetime
from uuid import UUID

from fastapi import HTTPException

from app.db.db import Database
from app.db.models.certificate import CertificateEntity
from app.db.models.client import ClientEntity
from app.db.models.organization import OrganizationEntity
from app.db.repository.organization import OrganizationRepository
from app.db.repository.query_builder.data import CertificateQueryContext, OrganizationQueryContext, SourceQueryContext
from app.db.repository.scope import ScopeRepository
from app.db.repository.source import SourceRepository
from app.models.organization import Organization, OrganizationCreate, OrganizationQueryParams, OrganizationUpdate
from app.services.certificate import OrganizationCertificateService
from app.services.certificate.client_certificate import ClientCertificateService
from app.services.exceptions import (
    ConflictError,
    OrganizationHasActiveClientsError,
    RecordNotFoundError,
    ScopeNotAllowedError,
)
from app.services.scopes import ScopeService
from app.services.source import SourceService


class OrganizationService:
    def __init__(self, db: Database) -> None:
        self.db = db

    def create_one(
        self,
        dto: OrganizationCreate,
    ) -> Organization:
        with self.db.get_db_session() as session:
            org_repo = session.get_repository(OrganizationRepository)
            org_entity = OrganizationEntity(
                external_id=dto.external_id,
                name=dto.name,
            )
            if dto.sanitized_scopes:
                scopes_repo = session.get_repository(ScopeRepository)
                app_scopes = scopes_repo.find_many()
                valid_scopes = ScopeService.validate_requested_scopes(app_scopes, dto.sanitized_scopes)
                if not valid_scopes:
                    raise ScopeNotAllowedError(dto.sanitized_scopes)

                org_scopes = [s for s in app_scopes if s.name in dto.sanitized_scopes]
                org_entity.scopes = org_scopes

            if dto.certificates:
                org_entity.certificates = [
                    CertificateEntity(organization_identifier=c.organization_identifier, domain=c.domain)
                    for c in dto.certificates
                ]

            if dto.sources:
                repo = session.get_repository(SourceRepository)
                existing_sources = repo.find_many_by_external_ids(dto.source_ids)
                if len(existing_sources) > 0:
                    raise ConflictError(
                        f"Sources with source_id {[s.source_id for s in existing_sources]} already exists"
                    )

                org_entity.sources = [s.into_entity() for s in dto.sources]

            if dto.clients:
                for client in dto.clients:
                    client_entitiy = ClientEntity(name=client.name, description=client.description)
                    if client.scopes:
                        # TODO: change santizied_scopes to return [] in case scope is empty
                        ScopeService.assert_scopes_granted(org_entity, client.sanatized_scopes or [])
                        client_scopes = ScopeService.make_client_scope_from_org(
                            org_entity, client_entitiy, client.sanatized_scopes or []
                        )
                        client_entitiy.scopes = client_scopes

                    if client.certificates:
                        client_certs = ClientCertificateService.get_client_certs_from_org(
                            org_entity, client.certificates
                        )
                        client_entitiy.certificates = client_certs

                    if client.sources:
                        client_sources = SourceService.get_client_sources_from_org(org_entity, client.sources or [])
                        client_entitiy.sources = client_sources

                    org_entity.clients.append(client_entitiy)

            new_org = org_repo.add_one(org_entity)

            return Organization.from_entity(new_org)

    def get_one(self, id: UUID) -> Organization | None:
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
        with self.db.get_db_session() as session:
            org_repo = session.get_repository(OrganizationRepository)
            ctx = OrganizationQueryContext(
                source_ctx=SourceQueryContext.default(), certificate_ctx=CertificateQueryContext.default()
            )
            org = org_repo.find(id, ctx)
            if not org:
                raise HTTPException(status_code=404)

            change_happened = not (OrganizationUpdate.from_entity(org) == dto)
            if change_happened is False:
                return OrganizationUpdate.from_entity(org)

            org.name = dto.name
            if dto.sanitized_scopes:
                scope_repo = session.get_repository(ScopeRepository)
                app_scope = scope_repo.find_many()
                valid_scopes = ScopeService.validate_requested_scopes(app_scope, dto.sanitized_scopes)
                if not valid_scopes:
                    raise ScopeNotAllowedError(dto.sanitized_scopes)

                org_scopes = [s for s in app_scope if s.name in dto.sanitized_scopes]
                org.scopes = org_scopes
            else:
                org.scopes = []

            if dto.certificates:
                update_certs = OrganizationCertificateService.compute_certs_to_update_from_org(org, dto.certificates)
                org.certificates = update_certs
            else:
                if org.certificates:
                    for cert in org.certificates:
                        if cert.deleted_at is None:
                            cert.deleted_at = datetime.now()

            if dto.sources:
                updated_sources = SourceService.compute_org_sources_for_update(org, dto.sources)
                org.sources = updated_sources
            else:
                if org.sources:
                    for source in org.sources:
                        if source.deleted_at is None:
                            source.deleted_at = datetime.now()

            session.add(org)
            session.commit()
            return OrganizationUpdate.from_entity(org)

    def delete_one(self, id: UUID) -> OrganizationEntity | None:
        with self.db.get_db_session() as session:
            repo = session.get_repository(OrganizationRepository)
            org = repo.find_one(id)
            if org is None:
                return None

            valid_for_delete = OrganizationService.validate_org_for_delete(org)
            if not valid_for_delete:
                raise OrganizationHasActiveClientsError(id)

            org.deleted_at = datetime.now()

            if org.scopes:
                org.scopes.clear()

            session.add(org)
            session.commit()
            session.session.refresh(org)

            return org

    @staticmethod
    def validate_org_for_delete(org: OrganizationEntity) -> bool:
        valid_for_delete = True
        if org.clients:
            valid_for_delete = any(c.deleted_at is not None for c in org.clients)

        if org.certificates:
            valid_for_delete = any(c.deleted_at is not None for c in org.certificates)

        if org.sources:
            valid_for_delete = any(s.deleted_at is not None for s in org.sources)

        return valid_for_delete
