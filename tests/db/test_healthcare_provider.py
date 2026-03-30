from uuid import uuid4

from app.db.models.healthcare_provider import HealthcareProviderEntity
from app.db.repository.healthcare_provider import HealthcareProvidersRepository
from app.models.oin_number import OinNumber
from app.models.ura_number import UraNumber


def test_add_one_success(
    healthcare_provider_repository: HealthcareProvidersRepository,
    healthcare_provider_entity: HealthcareProviderEntity,
) -> None:
    with healthcare_provider_repository.db_session:
        result = healthcare_provider_repository.add_one(healthcare_provider_entity)

        assert result == healthcare_provider_entity


def test_get_one_found(
    healthcare_provider_repository: HealthcareProvidersRepository,
    healthcare_provider_entity: HealthcareProviderEntity,
) -> None:
    with healthcare_provider_repository.db_session:
        healthcare_provider_repository.add_one(healthcare_provider_entity)

        result = healthcare_provider_repository.get_one(healthcare_provider_entity.id)

        assert result is not None
        assert result.id == healthcare_provider_entity.id


def test_get_one_not_found(
    healthcare_provider_repository: HealthcareProvidersRepository,
) -> None:
    with healthcare_provider_repository.db_session:
        result = healthcare_provider_repository.get_one(uuid4())

        assert result is None


def test_update_success(
    healthcare_provider_repository: HealthcareProvidersRepository,
    healthcare_provider_entity: HealthcareProviderEntity,
) -> None:
    with healthcare_provider_repository.db_session:
        healthcare_provider_repository.add_one(healthcare_provider_entity)

        new_name = "Updated Name"

        result = healthcare_provider_repository.update(
            id=healthcare_provider_entity.id,
            common_name=new_name,
        )

        assert result is not None
        assert result.common_name == new_name


def test_update_ignores_invalid_fields(
    healthcare_provider_repository: HealthcareProvidersRepository,
    healthcare_provider_entity: HealthcareProviderEntity,
) -> None:
    with healthcare_provider_repository.db_session:
        data = healthcare_provider_repository.add_one(healthcare_provider_entity)
        assert data is not None

        result = healthcare_provider_repository.update(
            id=data.id,
            non_existing_field="value",
        )

        assert result is None


def test_update_not_found(
    healthcare_provider_repository: HealthcareProvidersRepository,
) -> None:
    with healthcare_provider_repository.db_session:
        result = healthcare_provider_repository.update(uuid4(), name="Does not exist")

        assert result is None


def test_get_many_should_return_all_records(
    healthcare_provider_repository: HealthcareProvidersRepository,
    healthcare_provider_entity: HealthcareProviderEntity,
    ura_number: UraNumber,
) -> None:
    entity_2 = HealthcareProviderEntity(
        ura_number=ura_number.value,
        source_id="some_other_source_id",
        is_source=True,
        is_viewer=True,
        oin="some_oin",
        common_name="some_common_name",
        status="active",
    )
    entity_3 = HealthcareProviderEntity(
        ura_number=UraNumber("00000125").value,
        source_id="antoher-source-id",
        is_source=True,
        is_viewer=False,
        oin="antoher-oin",
        common_name="fake-name",
        status="active",
    )
    with healthcare_provider_repository.db_session:
        healthcare_provider_repository.add_one(healthcare_provider_entity)
        healthcare_provider_repository.add_one(entity_2)
        healthcare_provider_repository.add_one(entity_3)

        results = healthcare_provider_repository.get_many()

        assert len(results) == 3


def test_get_many_should_return_exact_as_per_query(
    healthcare_provider_repository: HealthcareProvidersRepository,
    healthcare_provider_entity: HealthcareProviderEntity,
    ura_number: UraNumber,
    oin: OinNumber,
) -> None:
    entity_2 = HealthcareProviderEntity(
        ura_number=ura_number.value,
        source_id="some_other_source_id",
        is_source=True,
        is_viewer=True,
        oin=oin.value,
        common_name="some_common_name",
        status="active",
    )
    entity_3 = HealthcareProviderEntity(
        ura_number=UraNumber("00000125").value,
        source_id="antoher-source-id",
        is_source=True,
        is_viewer=False,
        oin="antoher-oin",
        common_name="fake-name",
        status="active",
    )
    with healthcare_provider_repository.db_session:
        healthcare_provider_repository.add_one(healthcare_provider_entity)
        healthcare_provider_repository.add_one(entity_2)
        healthcare_provider_repository.add_one(entity_3)

        results = healthcare_provider_repository.get_many(ura_number=ura_number.value, oin=oin.value)

        assert len(results) == 2

        results = healthcare_provider_repository.get_many(
            ura_number=ura_number.value,
            oin=healthcare_provider_entity.oin,
            source_id=healthcare_provider_entity.source_id,
        )
        assert len(results) == 1


def test_many_should_return_empty_list_when_no_match_is_found(
    healthcare_provider_repository: HealthcareProvidersRepository,
    healthcare_provider_entity: HealthcareProviderEntity,
) -> None:
    with healthcare_provider_repository.db_session:
        healthcare_provider_repository.add_one(healthcare_provider_entity)

        results = healthcare_provider_repository.get_many(
            ura_number="00000157",
            source_id="some-unknown-source",
            oin="000012345678910",
        )

        assert len(results) == 0
