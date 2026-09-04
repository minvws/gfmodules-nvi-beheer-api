import asyncio
import json
from typing import Any
from unittest.mock import MagicMock

import gfmodules.logging as gflog
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from gfmodules.logging import LoggingStreams
from gfmodules.logging.middleware import RequestContextMiddleware
from gfmodules.logging.testing import capture_records, capture_stream, recorded_shutdown_reason
from pytest_mock import MockerFixture

from app import application
from app.config import Config, set_config
from app.logging.events import ACT_CN, Log
from tests.test_config import get_test_config


@pytest.fixture()
def use_config() -> Config:
    cfg = get_test_config()
    set_config(cfg)
    return cfg


def _run_lifespan() -> list[Any]:
    with capture_records(application.logger.name) as captured:

        async def _exercise() -> None:
            async with application._lifespan(MagicMock()):
                pass

        asyncio.run(_exercise())
    return [entry.record for entry in captured.entries]


def _records_for(event_id: str) -> list[Any]:
    return [rec for rec in _run_lifespan() if rec.event_id == event_id]


class TestLifespan:
    def test_reports_a_graceful_shutdown_on_exit(self, use_config: Config, mocker: MockerFixture) -> None:
        mocker.patch("app.application._read_version", return_value="9.9.9")

        stopped = _records_for(Log.SYS_APP_STOPPED.event_id)

        assert [rec.shutdown_reason for rec in stopped] == ["graceful"]

    def test_reports_the_signal_that_triggered_the_shutdown(self, use_config: Config, mocker: MockerFixture) -> None:
        mocker.patch("app.application._read_version", return_value="9.9.9")

        with recorded_shutdown_reason("signal:SIGTERM"):
            stopped = _records_for(Log.SYS_APP_STOPPED.event_id)

        assert [rec.shutdown_reason for rec in stopped] == ["signal:SIGTERM"]

    def test_emits_no_stopped_event_after_a_crash(self, use_config: Config, mocker: MockerFixture) -> None:
        mocker.patch("app.application._read_version", return_value="9.9.9")

        with recorded_shutdown_reason("crash"):
            assert _records_for(Log.SYS_APP_STOPPED.event_id) == []

    def test_the_started_event_reports_the_version_and_config_path(
        self, use_config: Config, mocker: MockerFixture
    ) -> None:
        mocker.patch("app.application._read_version", return_value="1.2.3")

        started = _records_for(Log.SYS_APP_STARTED.event_id)

        assert len(started) == 1
        assert started[0].version == "1.2.3"
        assert started[0].config_path is not None


class TestApplicationInit:
    def test_installs_the_logging_excepthook_and_signal_handlers(
        self, use_config: Config, mocker: MockerFixture
    ) -> None:
        install_excepthook = mocker.patch("app.application.gflog.install_excepthook")
        install_signal_handlers = mocker.patch("app.application.gflog.install_signal_handlers")
        configure = mocker.patch("app.application.gflog.configure")

        application.application_init()

        configure.assert_called_once()
        install_excepthook.assert_called_once_with(application.logger)
        install_signal_handlers.assert_called_once_with()

    def test_configures_logging_with_the_catalogue_and_the_acting_client_field(
        self, use_config: Config, mocker: MockerFixture
    ) -> None:
        configure = mocker.patch("app.application.gflog.configure")

        application.setup_logging()

        configure.assert_called_once_with(
            config=use_config.logging,
            loglevel=use_config.app.loglevel,
            catalogue=Log,
            extra_context_fields=(ACT_CN,),
        )


class TestStartupFailure:
    def test_logs_an_unhandled_exception_when_the_app_fails_to_build(self, mocker: MockerFixture) -> None:
        mocker.patch("app.application.application_init")
        mocker.patch("app.application.setup_fastapi", side_effect=RuntimeError("startup boom"))

        with (
            capture_records(application.logger.name) as captured,
            pytest.raises(RuntimeError),
        ):
            application.create_fastapi_app()

        records: list[Any] = [entry.record for entry in captured.entries]
        assert [record.event_id for record in records] == [Log.SYS_UNHANDLED_EXCEPTION.event_id]
        assert records[0].exception_type == "RuntimeError"
        assert records[0].exc_info is not None


class TestUnhandledExceptionHandler:
    @staticmethod
    def _app() -> FastAPI:
        fastapi = FastAPI()

        @fastapi.get("/boom")
        def boom() -> None:
            raise RuntimeError("explode")

        fastapi.add_exception_handler(Exception, application._unhandled_exception_handler)
        return fastapi

    def test_returns_500_and_routes_the_exception_to_app_and_siem(self) -> None:
        with (
            capture_stream(LoggingStreams.APP, application.logger.name) as app_stream,
            capture_stream(LoggingStreams.SIEM, application.logger.name) as siem_stream,
        ):
            response = TestClient(self._app(), raise_server_exceptions=False).get("/boom")

        assert response.status_code == 500
        assert json.loads(response.content) == {"error": "Internal server error"}
        assert app_stream[0]["exception_type"] == "RuntimeError"
        assert app_stream[0]["endpoint"] == "/boom"
        assert siem_stream[0]["exception_type"] == "RuntimeError"


class TestUserAgent:
    @staticmethod
    def _app() -> FastAPI:
        fastapi = FastAPI()

        @fastapi.get("/ping")
        def ping() -> dict[str, str]:
            return {"status": "ok"}

        fastapi.add_middleware(RequestContextMiddleware)
        return fastapi

    def test_the_access_record_carries_the_user_agent_the_caller_sent(self) -> None:
        with capture_stream(LoggingStreams.APP, gflog.access_logger_name()) as access_stream:
            TestClient(self._app()).get("/ping", headers={"User-Agent": "kube-probe/1.31"})

        assert access_stream[0]["user_agent"] == "kube-probe/1.31"
