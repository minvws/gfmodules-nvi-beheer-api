from collections.abc import Callable, Generator, Sequence
from typing import Any
from unittest.mock import patch

import pytest
from gfmodules.logging.testing import assert_event_emitted, capture_records
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.exc import DatabaseError, DataError, IntegrityError, OperationalError, PendingRollbackError

from app.config import ConfigDatabase
from app.db.db import Database
from app.db.models.organization import OrganizationEntity
from app.db.session import DbSession
from app.logging.events import Log
from tests.conftest import TEST_EXTERNAL_ID, TEST_ORG_NAME

REJECTED_VALUE = "x" * 300


class StringDataRightTruncation(Exception):
    class diag:
        table_name = "organizations"
        column_name = "name"


def _truncation_error() -> DataError:
    return DataError(
        "INSERT INTO organizations",
        {"name": REJECTED_VALUE},
        StringDataRightTruncation("value too long for type character varying(255)"),
    )


class UniqueViolation(Exception):
    class diag:
        table_name = "sources"
        constraint_name = "uq_sources_source_id_active"


def _unique_violation() -> IntegrityError:
    return IntegrityError(
        "UPDATE sources",
        {"source_id": REJECTED_VALUE},
        UniqueViolation(f"duplicate key value violates unique constraint, Key (source_id)=({REJECTED_VALUE})"),
    )


run_once_and_retried = pytest.mark.parametrize(
    "operation,run",
    [
        ("execute", lambda session: session.execute(select(OrganizationEntity))),
        ("flush", lambda session: session.flush()),
    ],
)


def _failing(*errors: Exception) -> Callable[..., Any]:
    """A callable raising each error in turn, then succeeding."""
    remaining: list[Exception] = list(errors)

    def call(*_args: Any, **_kwargs: Any) -> None:
        if remaining:
            raise remaining.pop(0)

    return call


@pytest.fixture()
def retrying_database() -> Generator[Database, None, None]:
    """A database with a non-empty backoff, so the retry loop is actually exercised."""
    database = Database(config_database=ConfigDatabase(dsn=SecretStr("sqlite:///:memory:"), retry_backoff=[0.01, 0.01]))
    database.generate_tables()
    yield database
    database.engine.dispose()


def test_commit_failure_is_not_masked_by_retry(retrying_database: Database) -> None:
    """
    A failed flush poisons the transaction and the rollback that clears it discards the
    staged entity. Retrying the commit would then succeed against an empty session and
    report success while nothing was written -- it must raise instead.
    """
    with retrying_database.get_db_session() as session:
        session.add(OrganizationEntity(external_id=TEST_EXTERNAL_ID, name=TEST_ORG_NAME))

        flaky = _failing(
            OperationalError("stmt", {}, Exception("connection refused")),
            PendingRollbackError("transaction has been rolled back"),
        )
        with patch.object(session.session, "commit", side_effect=flaky) as commit, pytest.raises(DatabaseError):
            session.commit()

        assert commit.call_count == 1, "commit must not be retried once its unit of work is lost"


def test_commit_failure_leaves_nothing_persisted(retrying_database: Database) -> None:
    """The insert must be absent afterwards -- and the caller must have been told."""
    with retrying_database.get_db_session() as session:
        session.add(OrganizationEntity(external_id=TEST_EXTERNAL_ID, name=TEST_ORG_NAME))

        flaky = _failing(OperationalError("stmt", {}, Exception("connection refused")))
        with patch.object(session.session, "commit", side_effect=flaky), pytest.raises(DatabaseError):
            session.commit()

    with retrying_database.get_db_session() as session:
        rows: Sequence[OrganizationEntity] = session.execute(select(OrganizationEntity)).scalars().all()
        assert rows == []


def test_reads_are_still_retried_after_a_rollback() -> None:
    """Rollback-and-retry remains valid recovery for statements that re-run from scratch."""
    database = Database(config_database=ConfigDatabase(dsn=SecretStr("sqlite:///:memory:"), retry_backoff=[0.01]))
    database.generate_tables()

    try:
        with database.get_db_session() as session:
            real_execute = session.session.execute
            flaky = [PendingRollbackError("transaction has been rolled back")]

            def execute(*args: Any, **kwargs: Any) -> Any:
                if flaky:
                    raise flaky.pop(0)
                return real_execute(*args, **kwargs)

            with patch.object(session.session, "execute", side_effect=execute):
                rows: Sequence[OrganizationEntity] = session.execute(select(OrganizationEntity)).scalars().all()

            assert rows == []
            assert not flaky, "the read should have been retried after the rollback"
    finally:
        database.engine.dispose()


def test_a_retried_connection_failure_is_logged_per_attempt(retrying_database: Database) -> None:
    with retrying_database.get_db_session() as session, capture_records("app") as records:
        flaky = _failing(
            OperationalError("stmt", {}, Exception("connection refused")),
            OperationalError("stmt", {}, Exception("connection refused")),
        )
        with patch.object(session.session, "execute", side_effect=flaky):
            session.execute(select(OrganizationEntity))

    attempts = [
        (entry.message["error_type"], entry.message["retry_attempt"], entry.message["backoff_seconds"])
        for entry in records.for_event(Log.DB_CONNECTION_FAILED)
    ]
    assert attempts == [("OperationalError", 1, 0.01), ("OperationalError", 2, 0.01)]


def test_the_last_connection_failure_is_logged_as_out_of_retries(retrying_database: Database) -> None:
    with retrying_database.get_db_session() as session, capture_records("app") as records:
        failures = [OperationalError("stmt", {}, Exception("connection refused")) for _ in range(3)]
        with patch.object(session.session, "execute", side_effect=_failing(*failures)), pytest.raises(DatabaseError):
            session.execute(select(OrganizationEntity))

    assert [entry.description for entry in records.for_event(Log.DB_CONNECTION_FAILED)] == [
        "Database connection failed, retrying",
        "Database connection failed, retrying",
        "Database connection failed, out of retries",
    ]


def test_a_connection_failure_during_commit_is_logged(retrying_database: Database) -> None:
    with retrying_database.get_db_session() as session, capture_records("app") as records:
        flaky = _failing(OperationalError("stmt", {}, Exception("connection refused")))
        with patch.object(session.session, "commit", side_effect=flaky), pytest.raises(DatabaseError):
            session.commit()

    assert_event_emitted(records, Log.DB_CONNECTION_FAILED, error_type="OperationalError")


@run_once_and_retried
def test_a_schema_error_is_logged_with_where_it_failed_but_not_the_value(
    retrying_database: Database, operation: str, run: Callable[[DbSession], Any]
) -> None:
    with (
        retrying_database.get_db_session() as session,
        capture_records("app") as records,
        patch.object(session.session, operation, side_effect=_truncation_error()),
        pytest.raises(DataError),
    ):
        run(session)

    entry = assert_event_emitted(
        records,
        Log.DB_SCHEMA_ERROR,
        exception_type="StringDataRightTruncation",
        table="organizations",
        column="name",
        value_length=len(REJECTED_VALUE),
        column_limit=255,
    )
    assert REJECTED_VALUE not in str(entry.payload)


@run_once_and_retried
def test_a_rejected_operation_is_logged_with_its_constraint_but_not_the_value(
    retrying_database: Database, operation: str, run: Callable[[DbSession], Any]
) -> None:
    with (
        retrying_database.get_db_session() as session,
        capture_records("app") as records,
        patch.object(session.session, operation, side_effect=_unique_violation()),
        pytest.raises(IntegrityError),
    ):
        run(session)

    entry = assert_event_emitted(
        records,
        Log.DB_OPERATION_FAILED,
        exception_type="UniqueViolation",
        table="sources",
        constraint="uq_sources_source_id_active",
    )
    assert REJECTED_VALUE not in str(entry.payload)
    assert [entry.description for entry in records if "Retrying" in entry.description] == []
