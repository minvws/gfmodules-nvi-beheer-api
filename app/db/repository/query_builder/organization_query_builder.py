from dataclasses import dataclass
from enum import Enum, auto
from typing import Self
from uuid import UUID

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import aliased, contains_eager, selectinload

from app.db.models.certificate import CertificateEntity
from app.db.models.client import ClientEntity
from app.db.models.organization import OrganizationEntity
from app.db.models.scope import ScopeEntity
from app.db.models.source import SourceEntity
from app.models.ura import UraNumber


class LoadStrategy(Enum):
    SELECTIN_LOAD = auto()
    OUTERJOIN_LOAD = auto()


@dataclass
class OrganizationClientQueryContext:
    id: UUID | None = None
    name: str | None = None
    description: str | None = None
    scopes: list[str] | None = None
    certificate_id: UUID | None = None
    certificate_organization_identifier: str | None = None
    certificate_domain: str | None = None
    source_id: UUID | None = None
    source_name: str | None = None
    include_certificates: bool = True
    include_sources: bool = True
    include_scopes: bool = True

    @classmethod
    def default(cls) -> Self:
        return cls()


class OrganizationQueryBuilder:
    def __init__(self, load_strategy: LoadStrategy = LoadStrategy.SELECTIN_LOAD, include_deleted: bool = False) -> None:
        self._stmt = select(OrganizationEntity)
        self._load_strategy: LoadStrategy = load_strategy
        self._include_deleted: bool = include_deleted

    def with_id(self, id: UUID | None) -> Self:
        if id is None:
            return self

        self._stmt = self._stmt.where(OrganizationEntity.id == id)
        return self

    def with_external_id(self, external_id: UraNumber | None) -> Self:
        if external_id is None:
            return self

        self._stmt = self._stmt.where(OrganizationEntity.external_id == external_id)
        return self

    def with_name(self, name: str | None) -> Self:
        if name is None:
            return self

        self._stmt = self._stmt.where(OrganizationEntity.name == name)
        return self

    def include_scopes(self, scopes: list[str] | None = None) -> Self:
        match self._load_strategy:
            case LoadStrategy.SELECTIN_LOAD:
                self._selectinload_scopes(scopes)
            case LoadStrategy.OUTERJOIN_LOAD:
                self._joinload_scopes(scopes)

        return self

    def _selectinload_scopes(self, scopes: list[str] | None = None) -> Self:
        attr = OrganizationEntity.scopes
        if scopes:
            attr = attr.and_(or_(*[ScopeEntity.name == s for s in scopes]))

        self._stmt = self._stmt.options(selectinload(attr))
        return self

    def _joinload_scopes(self, scopes: list[str] | None = None) -> Self:
        self._stmt = self._stmt.outerjoin(OrganizationEntity.scopes).options(contains_eager(OrganizationEntity.scopes))
        if scopes:
            self._stmt = self._stmt.where(or_(*[ScopeEntity.name == s for s in scopes]))

        return self

    def include_certificate(
        self,
        id: UUID | None = None,
        organization_identifier: str | None = None,
        domain: str | None = None,
    ) -> Self:
        match self._load_strategy:
            case LoadStrategy.OUTERJOIN_LOAD:
                self._joinload_cert(
                    id=id,
                    organization_identifier=organization_identifier,
                    domain=domain,
                )

            case LoadStrategy.SELECTIN_LOAD:
                self._selecinload_cert(
                    id=id,
                    organization_identifier=organization_identifier,
                    domain=domain,
                )

        return self

    def _selecinload_cert(
        self,
        id: UUID | None = None,
        organization_identifier: str | None = None,
        domain: str | None = None,
    ) -> Self:
        attr = OrganizationEntity.certificates
        conditions = []
        if id:
            conditions.append(CertificateEntity.id == id)

        if self._include_deleted is False:
            conditions.append(CertificateEntity.deleted_at.is_(None))

        if organization_identifier:
            conditions.append(CertificateEntity.organization_identifier == organization_identifier)

        if domain:
            conditions.append(CertificateEntity.domain == domain)

        if conditions:
            attr = attr.and_(*conditions)

        self._stmt = self._stmt.options(selectinload(attr))

        return self

    def _joinload_cert(
        self,
        id: UUID | None = None,
        organization_identifier: str | None = None,
        domain: str | None = None,
    ) -> Self:
        attr = OrganizationEntity.certificates
        conditions = []
        if self._include_deleted is False:
            conditions.append(CertificateEntity.deleted_at.is_(None))

        self._stmt = self._stmt.outerjoin(attr).options(contains_eager(OrganizationEntity.certificates))
        if id:
            conditions.append(CertificateEntity.id == id)

        if domain:
            conditions.append(CertificateEntity.domain == domain)

        if organization_identifier:
            conditions.append(CertificateEntity.organization_identifier == organization_identifier)

        if conditions:
            self._stmt = self._stmt.where(*conditions)

        return self

    def include_sources(self, id: UUID | None = None, name: str | None = None) -> Self:
        match self._load_strategy:
            case LoadStrategy.OUTERJOIN_LOAD:
                self._joinload_sources(id, name)
            case LoadStrategy.SELECTIN_LOAD:
                self._selectinload_sources(id, name)
        return self

    def _selectinload_sources(self, id: UUID | None = None, name: str | None = None) -> Self:
        attr = OrganizationEntity.sources
        conditions = []
        if id:
            conditions.append(SourceEntity.id == id)

        if name:
            conditions.append(SourceEntity.name == name)

        if self._include_deleted is False:
            conditions.append(SourceEntity.deleted_at.is_(None))

        if conditions:
            attr = attr.and_(*conditions)

        self._stmt = self._stmt.options(selectinload(attr))
        return self

    def _joinload_sources(self, id: UUID | None = None, name: str | None = None) -> Self:
        attr = OrganizationEntity.sources
        conditions = []

        if id:
            conditions.append(SourceEntity.id == id)
        if name:
            conditions.append(SourceEntity.name == name)
        if self._include_deleted is False:
            conditions.append(SourceEntity.deleted_at.is_(None))

        self._stmt = self._stmt.outerjoin(attr).options(contains_eager(OrganizationEntity.sources))

        if conditions:
            self._stmt = self._stmt.where(*conditions)

        return self

    def include_clients(
        self,
        ctx: OrganizationClientQueryContext = OrganizationClientQueryContext.default(),
    ) -> Self:

        match self._load_strategy:
            case LoadStrategy.OUTERJOIN_LOAD:
                self._joinload_client(ctx)
            case LoadStrategy.SELECTIN_LOAD:
                self._selectinload_client(ctx)

        return self

    def _selectinload_client(
        self,
        ctx: OrganizationClientQueryContext,
    ) -> Self:
        main_attr = OrganizationEntity.clients
        scope_attr = ClientEntity.scopes
        if ctx.id:
            main_attr = main_attr.and_(ClientEntity.id == ctx.id)

        if self._include_deleted is False:
            main_attr = main_attr.and_(ClientEntity.deleted_at.is_(None))

        load_options = []

        if ctx.include_scopes:
            scope_attr = ClientEntity.scopes
            if ctx.scopes:
                scope_attr = scope_attr.and_(or_(*[ScopeEntity.name == s for s in ctx.scopes]))

            load_options.append(selectinload(main_attr).selectinload(scope_attr))

        if ctx.include_certificates:
            cert_conditions = []
            cert_attr = ClientEntity.certificates
            if ctx.certificate_id:
                cert_conditions.append(CertificateEntity.id == ctx.certificate_id)

            if ctx.certificate_organization_identifier:
                cert_conditions.append(
                    CertificateEntity.organization_identifier == ctx.certificate_organization_identifier
                )

            if ctx.certificate_domain:
                cert_conditions.append(CertificateEntity.domain == ctx.certificate_domain)

            if self._include_deleted is False:
                cert_conditions.append(CertificateEntity.deleted_at.is_(None))

            if cert_conditions:
                cert_attr = cert_attr.and_(*cert_conditions)

            load_options.append(selectinload(main_attr).selectinload(cert_attr))

        if ctx.include_sources:
            src_attr = ClientEntity.sources
            src_conditions = []
            if ctx.source_id:
                src_conditions.append(SourceEntity.id == ctx.source_id)

            if ctx.source_name:
                src_conditions.append(SourceEntity.name == ctx.source_name)

            if self._include_deleted is False:
                src_conditions.append(SourceEntity.deleted_at.is_(None))

            if src_conditions:
                src_attr = src_attr.and_(*src_conditions)

            load_options.append(selectinload(main_attr).selectinload(src_attr))

        self._stmt = self._stmt.options(*load_options)
        return self

    def _joinload_client(
        self,
        ctx: OrganizationClientQueryContext,
    ):

        ClientCertificateAlias = aliased(CertificateEntity, name="client_certificate")
        ClientSourceAlias = aliased(SourceEntity, name="client_source")
        ClientScopeAlias = aliased(ScopeEntity, name="client_scope")
        options = [contains_eager(OrganizationEntity.clients)]

        attr = OrganizationEntity.clients

        self._stmt = self._stmt.outerjoin(attr)

        if ctx.include_scopes:
            self._stmt = self._stmt.outerjoin(ClientEntity.scopes.of_type(ClientScopeAlias))
            options.append(
                contains_eager(OrganizationEntity.clients).contains_eager(ClientEntity.scopes, alias=ClientScopeAlias)
            )

        if ctx.include_certificates:
            cert_attr = ClientEntity.certificates.of_type(ClientCertificateAlias)

            self._stmt = self._stmt.outerjoin(cert_attr)
            cert_option = contains_eager(OrganizationEntity.clients).contains_eager(
                ClientEntity.certificates, alias=ClientCertificateAlias
            )
            options.append(cert_option)

        if ctx.include_sources:
            src_attr = ClientEntity.sources.of_type(ClientSourceAlias)

            self._stmt = self._stmt.outerjoin(src_attr)
            src_option = contains_eager(OrganizationEntity.clients).contains_eager(
                ClientEntity.sources, alias=ClientSourceAlias
            )
            options.append(src_option)

        self._stmt = self._stmt.options(*options)

        conditions = []
        if ctx.id:
            conditions.append(ClientEntity.id == ctx.id)
        if ctx.name:
            conditions.append(ClientEntity.name == ctx.name)
        if ctx.description:
            conditions.append(ClientEntity.description == ctx.description)
        if ctx.scopes:
            conditions.append(*[ClientScopeAlias.name == s for s in ctx.scopes])

        if ctx.certificate_id:
            conditions.append(ClientCertificateAlias.id == ctx.certificate_id)

        if ctx.certificate_organization_identifier:
            conditions.append(ClientCertificateAlias.organization_identifier == ctx.certificate_organization_identifier)
        if ctx.certificate_domain:
            conditions.append(ClientCertificateAlias.domain == ctx.certificate_domain)
        if ctx.source_id:
            conditions.append(ClientSourceAlias.id == ctx.source_id)
        if ctx.source_name:
            conditions.append(ClientSourceAlias.name == ctx.source_name)

        if self._include_deleted is False:
            conditions.extend(
                [
                    ClientEntity.deleted_at.is_(None),
                    ClientCertificateAlias.deleted_at.is_(None),
                    ClientSourceAlias.deleted_at.is_(None),
                ]
            )

        if conditions:
            self._stmt = self._stmt.where(*conditions)

        return self

    def build(self) -> Select[tuple[OrganizationEntity]]:
        return self._stmt
