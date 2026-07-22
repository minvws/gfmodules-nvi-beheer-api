from typing import Any, Callable, List
from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.exc import DatabaseError, OperationalError, PendingRollbackError

from app.config import ConfigDatabase
from app.db.db import Database
from app.db.models.organization import OrganizationEntity
from tests.conftest import TEST_ORG_NAME, TEST_REGISTER_ID


def _failing(*errors: Exception) -> Callable[..., Any]:
    """A callable raising each error in turn, then succeeding."""
    remaining: List[Exception] = list(errors)

    def call(*_args: Any, **_kwargs: Any) -> None:
        if remaining:
            raise remaining.pop(0)

    return call


@pytest.fixture()
def retrying_database() -> Database:
    """A database with a non-empty backoff, so the retry loop is actually exercised."""
    database = Database(config_database=ConfigDatabase(dsn="sqlite:///:memory:", retry_backoff=[0.01, 0.01]))
    database.generate_tables()
    return database


def test_commit_failure_is_not_masked_by_retry(retrying_database: Database) -> None:
    """
    A failed flush poisons the transaction and the rollback that clears it discards the
    staged entity. Retrying the commit would then succeed against an empty session and
    report success while nothing was written -- it must raise instead.
    """
    with retrying_database.get_db_session() as session:
        session.add(OrganizationEntity(register_id=TEST_REGISTER_ID, name=TEST_ORG_NAME))

        flaky = _failing(
            OperationalError("stmt", {}, Exception("connection refused")),
            PendingRollbackError("transaction has been rolled back"),
        )
        with patch.object(session.session, "commit", side_effect=flaky) as commit:
            with pytest.raises(DatabaseError):
                session.commit()

        assert commit.call_count == 1, "commit must not be retried once its unit of work is lost"


def test_commit_failure_leaves_nothing_persisted(retrying_database: Database) -> None:
    """The insert must be absent afterwards -- and the caller must have been told."""
    with retrying_database.get_db_session() as session:
        session.add(OrganizationEntity(register_id=TEST_REGISTER_ID, name=TEST_ORG_NAME))

        flaky = _failing(OperationalError("stmt", {}, Exception("connection refused")))
        with patch.object(session.session, "commit", side_effect=flaky):
            with pytest.raises(DatabaseError):
                session.commit()

    with retrying_database.get_db_session() as session:
        rows = session.execute(select(OrganizationEntity)).scalars().all()
        assert rows == []


def test_reads_are_still_retried_after_a_rollback() -> None:
    """Rollback-and-retry remains valid recovery for statements that re-run from scratch."""
    database = Database(config_database=ConfigDatabase(dsn="sqlite:///:memory:", retry_backoff=[0.01]))
    database.generate_tables()

    with database.get_db_session() as session:
        real_execute = session.session.execute
        flaky = [PendingRollbackError("transaction has been rolled back")]

        def execute(*args: Any, **kwargs: Any) -> Any:
            if flaky:
                raise flaky.pop(0)
            return real_execute(*args, **kwargs)

        with patch.object(session.session, "execute", side_effect=execute):
            rows = session.execute(select(OrganizationEntity)).scalars().all()

        assert rows == []
        assert not flaky, "the read should have been retried after the rollback"
