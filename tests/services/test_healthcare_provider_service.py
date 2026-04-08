from uuid import UUID, uuid4

from app.db.models.healthcare_provider import HealthcareProviderEntity
from app.services.healthcare_provider import HeatlhcareProviderService


def test_create_one_should_succeed(
    healthcare_provider_service: HeatlhcareProviderService,
    healthcare_provider_entity: HealthcareProviderEntity,
) -> None:
    data = healthcare_provider_service.create_one(
        ura_number=healthcare_provider_entity.ura_number,
        source_id=healthcare_provider_entity.source_id,
        is_source=healthcare_provider_entity.is_source,
        is_viewer=healthcare_provider_entity.is_viewer,
        oin=healthcare_provider_entity.oin,
        common_name=healthcare_provider_entity.common_name,
        status=healthcare_provider_entity.status,
    )

    for key in healthcare_provider_entity.__table__.columns.keys():
        expected_attr = getattr(healthcare_provider_entity, key)
        actual_attr = getattr(data, key)

        if key == "id":
            assert isinstance(actual_attr, UUID)
            continue

        assert expected_attr == actual_attr


def test_get_one_should_succeed(
    healthcare_provider_service: HeatlhcareProviderService,
    healthcare_provider_entity: HealthcareProviderEntity,
) -> None:
    expected = healthcare_provider_service.create_one(
        ura_number=healthcare_provider_entity.ura_number,
        source_id=healthcare_provider_entity.source_id,
        is_source=healthcare_provider_entity.is_source,
        is_viewer=healthcare_provider_entity.is_viewer,
        oin=healthcare_provider_entity.oin,
        common_name=healthcare_provider_entity.common_name,
        status=healthcare_provider_entity.status,
    )

    actual = healthcare_provider_service.get_one(expected.id)

    for key in healthcare_provider_entity.__table__.columns.keys():
        expected_attr = getattr(expected, key)
        actual_attr = getattr(actual, key)

        assert expected_attr == actual_attr


def test_get_one_should_return_none_when_does_not_exist(
    healthcare_provider_service: HeatlhcareProviderService,
    healthcare_provider_entity: HealthcareProviderEntity,
) -> None:
    healthcare_provider_service.create_one(
        ura_number=healthcare_provider_entity.ura_number,
        source_id=healthcare_provider_entity.source_id,
        is_source=healthcare_provider_entity.is_source,
        is_viewer=healthcare_provider_entity.is_viewer,
        oin=healthcare_provider_entity.oin,
        common_name=healthcare_provider_entity.common_name,
        status=healthcare_provider_entity.status,
    )

    actual = healthcare_provider_service.get_one(uuid4())

    assert actual is None


def test_delete_one_should_succeed(
    healthcare_provider_service: HeatlhcareProviderService,
    healthcare_provider_entity: HealthcareProviderEntity,
) -> None:
    data = healthcare_provider_service.create_one(
        ura_number=healthcare_provider_entity.ura_number,
        source_id=healthcare_provider_entity.source_id,
        is_source=healthcare_provider_entity.is_source,
        is_viewer=healthcare_provider_entity.is_viewer,
        oin=healthcare_provider_entity.oin,
        common_name=healthcare_provider_entity.common_name,
        status=healthcare_provider_entity.status,
    )

    healthcare_provider_service.delete_one(data.id)
    actual = healthcare_provider_service.get_one(data.id)

    assert actual is None


def test_update_one_should_succeed(
    healthcare_provider_service: HeatlhcareProviderService,
    healthcare_provider_entity: HealthcareProviderEntity,
) -> None:
    data = healthcare_provider_service.create_one(
        ura_number=healthcare_provider_entity.ura_number,
        source_id=healthcare_provider_entity.source_id,
        is_source=healthcare_provider_entity.is_source,
        is_viewer=healthcare_provider_entity.is_viewer,
        oin=healthcare_provider_entity.oin,
        common_name=healthcare_provider_entity.common_name,
        status=healthcare_provider_entity.status,
    )

    expected = healthcare_provider_service.update_one(data.id, common_name="some-other-name")
    assert expected is not None
    assert expected.common_name == "some-other-name"
    assert expected.id == data.id


def test_update_one_should_ignore_unkown_attrs(
    healthcare_provider_service: HeatlhcareProviderService,
    healthcare_provider_entity: HealthcareProviderEntity,
) -> None:
    data = healthcare_provider_service.create_one(
        ura_number=healthcare_provider_entity.ura_number,
        source_id=healthcare_provider_entity.source_id,
        is_source=healthcare_provider_entity.is_source,
        is_viewer=healthcare_provider_entity.is_viewer,
        oin=healthcare_provider_entity.oin,
        common_name=healthcare_provider_entity.common_name,
        status=healthcare_provider_entity.status,
    )

    expected = healthcare_provider_service.update_one(data.id, some_attr="fake data")
    assert expected is None


def test_update_one_should_return_none_when_nothing_to_update(
    healthcare_provider_service: HeatlhcareProviderService,
    healthcare_provider_entity: HealthcareProviderEntity,
) -> None:
    data = healthcare_provider_service.create_one(
        ura_number=healthcare_provider_entity.ura_number,
        source_id=healthcare_provider_entity.source_id,
        is_source=healthcare_provider_entity.is_source,
        is_viewer=healthcare_provider_entity.is_viewer,
        oin=healthcare_provider_entity.oin,
        common_name=healthcare_provider_entity.common_name,
        status=healthcare_provider_entity.status,
    )

    expected = healthcare_provider_service.update_one(data.id)
    assert expected is None


def test_get_all_should_succeed(
    healthcare_provider_service: HeatlhcareProviderService,
    healthcare_provider_entity: HealthcareProviderEntity,
) -> None:
    data = healthcare_provider_service.create_one(
        ura_number=healthcare_provider_entity.ura_number,
        source_id=healthcare_provider_entity.source_id,
        is_source=healthcare_provider_entity.is_source,
        is_viewer=healthcare_provider_entity.is_viewer,
        oin=healthcare_provider_entity.oin,
        common_name=healthcare_provider_entity.common_name,
        status=healthcare_provider_entity.status,
    )
    data2 = healthcare_provider_service.create_one(
        ura_number="00000456",
        source_id=healthcare_provider_entity.source_id,
        is_source=healthcare_provider_entity.is_source,
        is_viewer=healthcare_provider_entity.is_viewer,
        oin=healthcare_provider_entity.oin,
        common_name=healthcare_provider_entity.common_name,
        status=healthcare_provider_entity.status,
    )

    expected = healthcare_provider_service.get_all()
    assert len(expected) == 2
    assert expected[0].id == data.id
    assert expected[1].id == data2.id


def test_get_all_should_return_empty_list_when_no_data(
    healthcare_provider_service: HeatlhcareProviderService,
) -> None:
    expected = healthcare_provider_service.get_all()
    assert expected == []


def test_get_all_should_return_only_non_deleted_data(
    healthcare_provider_service: HeatlhcareProviderService,
    healthcare_provider_entity: HealthcareProviderEntity,
) -> None:
    data = healthcare_provider_service.create_one(
        ura_number=healthcare_provider_entity.ura_number,
        source_id=healthcare_provider_entity.source_id,
        is_source=healthcare_provider_entity.is_source,
        is_viewer=healthcare_provider_entity.is_viewer,
        oin=healthcare_provider_entity.oin,
        common_name=healthcare_provider_entity.common_name,
        status=healthcare_provider_entity.status,
    )
    healthcare_provider_service.delete_one(data.id)

    expected = healthcare_provider_service.get_all()
    assert expected == []
