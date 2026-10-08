import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from app import application
from app.config import set_config
from tests.test_config import get_test_config


@pytest.mark.parametrize("swagger_enabled", [True, False])
def test_setup_fastapi_should_apply_root_path(mocker: MockerFixture, swagger_enabled: bool) -> None:
    mocker.patch("app.application.container.configure")
    config = get_test_config()
    config.uvicorn.swagger_enabled = swagger_enabled
    config.uvicorn.root_path = "/nvi-beheer"
    set_config(config)

    app = application.setup_fastapi()

    assert app.root_path == "/nvi-beheer"
    assert app.title == "NVI Beheer API"


def test_setup_fastapi_should_disable_docs_when_swagger_disabled(mocker: MockerFixture) -> None:
    mocker.patch("app.application.container.configure")
    config = get_test_config()
    config.uvicorn.swagger_enabled = False
    set_config(config)

    client = TestClient(application.setup_fastapi())

    assert client.get(config.uvicorn.docs_url).status_code == 404
    assert client.get(config.uvicorn.redoc_url).status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_setup_fastapi_should_serve_openapi_when_swagger_enabled(mocker: MockerFixture) -> None:
    mocker.patch("app.application.container.configure")
    set_config(get_test_config())

    client = TestClient(application.setup_fastapi())

    assert client.get("/openapi.json").status_code == 200
