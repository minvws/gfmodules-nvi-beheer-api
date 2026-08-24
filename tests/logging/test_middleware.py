from typing import Any, Iterator

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from starlette.requests import Request

from app.application import setup_fastapi
from app.config import set_config
from app.logging.context import (
    CLIENT_CN_HEADER,
    CLIENT_TRACE_ID_HEADER,
    CORRELATION_ID_HEADER,
    REQUEST_ID_HEADER,
    UNSET,
    correlation_id_var,
    endpoint_var,
    method_var,
    request_id_var,
    x_gf_act_cn_var,
)
from app.logging.middleware import RequestContextMiddleware, restore_request_context
from tests.test_config import get_test_config

CORRELATION_ID = "some-generated-id"


@restore_request_context
def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"correlation_id": correlation_id_var.get(), "request_id": request_id_var.get()},
    )


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = FastAPI()

    @app.get("/echo")
    def echo() -> dict[str, Any]:
        return {
            "correlation_id": correlation_id_var.get(),
            "request_id": request_id_var.get(),
            "endpoint": endpoint_var.get(),
            "method": method_var.get(),
            "gf-act-cn": x_gf_act_cn_var.get(),
        }

    @app.post("/echo")
    def echo_post(payload: dict[str, Any]) -> dict[str, Any]:
        return {"correlation_id": correlation_id_var.get(), "payload": payload}

    @app.get("/boom")
    def boom() -> dict[str, Any]:
        raise RuntimeError("kaboom")

    app.add_middleware(RequestContextMiddleware)
    app.add_exception_handler(Exception, _unhandled_exception_handler)

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def test_inbound_correlation_id_reaches_the_endpoint(client: TestClient) -> None:
    response = client.get("/echo", headers={CORRELATION_ID_HEADER: CORRELATION_ID})

    assert response.json()["correlation_id"] == CORRELATION_ID


def test_correlation_id_is_echoed_on_the_response(client: TestClient) -> None:
    response = client.get("/echo", headers={CORRELATION_ID_HEADER: CORRELATION_ID})

    assert response.headers[CORRELATION_ID_HEADER] == CORRELATION_ID
    assert response.headers[REQUEST_ID_HEADER]


def test_missing_correlation_id_is_not_invented_or_echoed(client: TestClient) -> None:
    response = client.get("/echo")

    assert response.json()["correlation_id"] == UNSET
    assert CORRELATION_ID_HEADER not in response.headers


def test_correlation_id_header_lookup_is_case_insensitive(client: TestClient) -> None:
    response = client.get("/echo", headers={"x-gf-correlation-id": CORRELATION_ID})

    assert response.json()["correlation_id"] == CORRELATION_ID


def test_unsafe_characters_are_stripped(client: TestClient) -> None:
    response = client.get("/echo", headers={CORRELATION_ID_HEADER: "abc$%^123"})

    assert response.json()["correlation_id"] == "abc123"


def test_correlation_id_is_truncated(client: TestClient) -> None:
    response = client.get("/echo", headers={CORRELATION_ID_HEADER: "a" * 200})

    assert response.json()["correlation_id"] == "a" * 64


def test_fully_unsafe_correlation_id_falls_back_to_the_sentinel(client: TestClient) -> None:
    # Sanitizing to an empty string must not yield an empty header value.
    response = client.get("/echo", headers={CORRELATION_ID_HEADER: "$$$"})

    assert response.json()["correlation_id"] == UNSET
    assert CORRELATION_ID_HEADER not in response.headers


def test_client_trace_id_is_echoed_alongside(client: TestClient) -> None:
    response = client.get("/echo", headers={CLIENT_TRACE_ID_HEADER: "trace-1"})

    assert response.headers[CLIENT_TRACE_ID_HEADER] == "trace-1"


def test_endpoint_method_and_client_cn_are_still_bound(client: TestClient) -> None:
    body = client.get("/echo", headers={CLIENT_CN_HEADER: "some-cn"}).json()

    assert body["endpoint"] == "/echo"
    assert body["method"] == "GET"
    assert body["gf-act-cn"] == "some-cn"


def test_request_body_is_still_readable_by_the_endpoint(client: TestClient) -> None:
    # The middleware consumes the body to log it and replays it via a new receive().
    response = client.post("/echo", json={"a": 1})

    assert response.json()["payload"] == {"a": 1}


def test_an_upstream_request_id_is_reused(client: TestClient) -> None:
    first = client.get("/echo")

    assert first.json()["request_id"] == first.headers[REQUEST_ID_HEADER]


def test_context_is_restored_for_an_unhandled_exception(client: TestClient) -> None:
    response = client.get("/boom", headers={CORRELATION_ID_HEADER: CORRELATION_ID})

    assert response.status_code == 500
    assert response.json()["correlation_id"] == CORRELATION_ID
    assert response.json()["request_id"] != UNSET


def test_correlation_id_is_echoed_on_a_500(client: TestClient) -> None:
    response = client.get("/boom", headers={CORRELATION_ID_HEADER: CORRELATION_ID})

    assert response.headers[CORRELATION_ID_HEADER] == CORRELATION_ID
    assert response.headers[REQUEST_ID_HEADER]


def test_context_does_not_leak_between_requests(client: TestClient) -> None:
    client.get("/echo", headers={CORRELATION_ID_HEADER: CORRELATION_ID})

    assert client.get("/echo").json()["correlation_id"] == UNSET
    assert correlation_id_var.get() == UNSET


def test_each_request_gets_a_distinct_request_id(client: TestClient) -> None:
    first = client.get("/echo").headers[REQUEST_ID_HEADER]
    second = client.get("/echo").headers[REQUEST_ID_HEADER]

    assert first != second


def test_real_app_keeps_correlation_context_on_an_unhandled_exception(
    mocker: MockerFixture,
) -> None:
    set_config(get_test_config())
    app = setup_fastapi()

    @app.get("/__boom")
    def boom() -> dict[str, Any]:
        raise RuntimeError("kaboom")

    logged: dict[str, str] = {}

    def capture(*args: Any, **kwargs: Any) -> None:
        logged["correlation_id"] = correlation_id_var.get()
        logged["request_id"] = request_id_var.get()

    mocker.patch("app.application.Log.event", side_effect=capture)

    response = TestClient(app, raise_server_exceptions=False).get(
        "/__boom", headers={CORRELATION_ID_HEADER: CORRELATION_ID}
    )

    assert response.status_code == 500
    assert response.headers[CORRELATION_ID_HEADER] == CORRELATION_ID
    assert response.headers[REQUEST_ID_HEADER]
    assert logged["correlation_id"] == CORRELATION_ID
    assert logged["request_id"] == response.headers[REQUEST_ID_HEADER]


def test_handler_still_responds_when_no_context_was_bound() -> None:
    # Without RequestContextMiddleware there is nothing to rebind; the handler must not blow up.
    app = FastAPI()

    @app.get("/boom")
    def boom() -> dict[str, Any]:
        raise RuntimeError("kaboom")

    app.add_exception_handler(Exception, _unhandled_exception_handler)

    response = TestClient(app, raise_server_exceptions=False).get("/boom")

    assert response.status_code == 500
    assert response.json()["correlation_id"] == UNSET
    assert REQUEST_ID_HEADER not in response.headers
