"""The routing layer maps every domain exception to exactly one status code."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from gfmodules.logging import LoggingStreams
from gfmodules.logging.testing import assert_event_emitted, capture_records, capture_stream
from pytest_mock import MockerFixture

from app import application, exceptions
from app.config import set_config
from app.exceptions import DomainError, ScopesNotGrantedError
from app.logging.events import Log
from app.models.scopes import AuthorizationScope
from app.routers.errors import STATUS_CODES, domain_error_handler, install_domain_error_handler, status_code_for
from tests.test_config import get_test_config


def _all_domain_errors() -> list[type[DomainError]]:
    return [
        cls
        for cls in vars(exceptions).values()
        if isinstance(cls, type) and issubclass(cls, DomainError) and cls is not DomainError
    ]


def test_every_domain_error_has_a_status_code() -> None:
    unmapped = [cls.__name__ for cls in _all_domain_errors() if cls not in STATUS_CODES]
    assert unmapped == []


def test_every_domain_error_has_a_reason_of_its_own() -> None:
    reasons = [cls.reason for cls in _all_domain_errors()]
    assert DomainError.reason not in reasons
    assert len(reasons) == len(set(reasons))


def test_every_mapped_status_code_is_a_client_error() -> None:
    assert all(400 <= code < 500 for code in STATUS_CODES.values())


def test_subclasses_inherit_the_mapping_of_their_parent() -> None:
    class MoreSpecificConflictError(exceptions.ConflictError):
        pass

    assert status_code_for(MoreSpecificConflictError()) == 409


def test_unmapped_domain_error_is_an_internal_error() -> None:
    class Unmapped(DomainError):
        pass

    assert status_code_for(Unmapped()) == 500


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    install_domain_error_handler(app)

    @app.get("/refuse")
    def refuse() -> None:
        raise exceptions.ForbiddenOperationError()

    @app.get("/with-arguments")
    def with_arguments() -> None:
        raise ScopesNotGrantedError(set(AuthorizationScope))

    @app.get("/custom-message")
    def custom_message() -> None:
        raise exceptions.ConflictError("Organization external_id 1234 already exists")

    return TestClient(app)


def test_handler_answers_with_the_mapped_code_and_the_message(client: TestClient) -> None:
    response = client.get("/refuse")

    assert response.status_code == 403
    assert response.json() == {"detail": "Operation is not allowed"}


def test_handler_includes_the_arguments_in_the_message(client: TestClient) -> None:
    response = client.get("/with-arguments")

    expected = ", ".join(sorted(s.value for s in AuthorizationScope))
    assert response.status_code == 403
    assert response.json() == {"detail": f"Scopes not granted by the organization: {expected}"}


def test_handler_uses_the_message_given_at_raise_time(client: TestClient) -> None:
    response = client.get("/custom-message")

    assert response.status_code == 409
    assert response.json() == {"detail": "Organization external_id 1234 already exists"}


def test_a_refusal_reaches_the_app_stream_only_with_its_reason_and_status(client: TestClient) -> None:
    with capture_stream(LoggingStreams.APP, "app") as app, capture_stream(LoggingStreams.SIEM, "app") as siem:
        client.get("/custom-message")

    assert [message for message in app if "error_reason" in message] == [
        {"error_reason": "conflict", "status_code": 409}
    ]
    assert siem == []


@pytest.mark.parametrize("stream", [LoggingStreams.APP, LoggingStreams.SIEM])
def test_a_forbidden_request_reaches_the_stream_with_its_reason_and_status(
    client: TestClient, stream: LoggingStreams
) -> None:
    with capture_stream(stream, "app") as messages:
        client.get("/refuse")

    forbidden = [message for message in messages if "error_reason" in message]
    assert forbidden == [{"error_reason": "forbidden_operation", "status_code": 403}]


def test_a_refusal_does_not_log_the_message_it_answers_with(client: TestClient) -> None:
    with capture_records("app") as records:
        client.get("/custom-message")

    entry = assert_event_emitted(records, Log.REQUEST_REFUSED)
    assert "already exists" not in str(entry.payload)


def test_application_registers_the_domain_error_handler(mocker: MockerFixture) -> None:
    mocker.patch("app.application.container.configure")
    set_config(get_test_config())

    app = application.setup_fastapi()

    assert app.exception_handlers[DomainError] is domain_error_handler
