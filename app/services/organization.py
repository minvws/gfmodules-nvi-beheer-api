from datetime import datetime
from uuid import UUID

from fastapi import HTTPException

from app.db.db import Database
from app.db.models.certificate import CertificateEntity
from app.db.models.organization import OrganizationEntity
from app.db.repository.organization import OrganizationRepository
from app.db.repository.scope import ScopeRepository
from app.db.repository.source import SourceRepository
from app.models.organization import Organization, OrganizationCreate, OrganizationUpdate
from app.models.ura import UraNumber
from app.services.certificate import CertificateService
from app.services.exceptions import (
    ConflictError,
    OrganizationHasActiveClientsError,
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
            entity = OrganizationEntity(
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
                entity.scopes = org_scopes

            if dto.certificates:
                entity.certificates = [
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

                entity.sources = [s.into_entity() for s in dto.sources]

            # TODO: add clients also
            new_org = org_repo.add_one(entity)

            return Organization.from_entity(new_org)

    def get_one(self, id: UUID, with_clients: bool = False) -> OrganizationEntity | None:
        with self.db.get_db_session() as session:
            repo = session.get_repository(OrganizationRepository)
            entity = repo.find_one(id, with_clients=with_clients)
            return entity

    def exists(self, id: UUID) -> bool:
        with self.db.get_db_session() as session:
            repo = session.get_repository(OrganizationRepository)
            return repo.exists(id)

    def get_many(
        self,
        external_id: UraNumber | None = None,
        name: str | None = None,
        scopes: list[str] | None = None,
        cert_identifier: str | None = None,
        cert_domain: str | None = None,
        include_deleted: bool = False,
    ) -> list[OrganizationEntity]:
        with self.db.get_db_session() as session:
            repo = session.get_repository(OrganizationRepository)
            orgs = repo.find_many(
                external_id=external_id,
                name=name,
                scopes=scopes,
                cert_identifier=cert_identifier,
                cert_domain=cert_domain,
                include_deleted=include_deleted,
            )
            return list(orgs)

    def update_one(self, id: UUID, dto: OrganizationUpdate) -> OrganizationEntity:
        with self.db.get_db_session() as session:
            org_repo = session.get_repository(OrganizationRepository)
            org = org_repo.find_one(id, include_deleted=True)
            if not org:
                raise HTTPException(status_code=404)

            change_happened = not (OrganizationUpdate.from_entity(org) == dto)
            if change_happened is False:
                print("\n\nNothin has changed here\n\n")
                return org

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
                update_certs = CertificateService.compute_certs_to_update_from_org(org, dto.certificates)
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

            # TODO: return dto with filtered deleted objects
            updated_org = org_repo.find_one_by_id(org.id)
            return updated_org

    def delete_one(self, id: UUID) -> OrganizationEntity | None:
        with self.db.get_db_session() as session:
            repo = session.get_repository(OrganizationRepository)
            org = repo.find_one(id, with_clients=True)
            if org is None:
                return None

            valid_for_delete = OrganizationService.validate_org_for_delete(org)
            if not valid_for_delete:
                raise OrganizationHasActiveClientsError(id)

            if org.clients and any(client.deleted_at is None for client in org.clients):
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
