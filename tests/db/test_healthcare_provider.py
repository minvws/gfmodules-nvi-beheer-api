from uuid import uuid4

from app.db.models.healthcare_provider import HealthcareProviderEntity
from app.db.repository.healthcare_provider import HealthcareProvidersRepository


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


def test_get_all(
    healthcare_provider_repository: HealthcareProvidersRepository,
    healthcare_provider_entity: HealthcareProviderEntity,
) -> None:
    with healthcare_provider_repository.db_session:
        healthcare_provider_repository.add_one(healthcare_provider_entity)

        result = healthcare_provider_repository.get_all()

        assert len(result) == 1
        assert result[0].id == healthcare_provider_entity.id


def test_get_all_returns_empty_list_when_no_data(
    healthcare_provider_repository: HealthcareProvidersRepository,
) -> None:
    with healthcare_provider_repository.db_session:
        result = healthcare_provider_repository.get_all()

        assert result == []
