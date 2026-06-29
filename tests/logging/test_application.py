import asyncio
import importlib
import json
import signal
import sys
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from app import application
from app.config import Config, set_config
from app.logging.events import Log
from tests.test_config import get_test_config


@pytest.fixture()
def use_config() -> Config:
    cfg = get_test_config()
    set_config(cfg)
    return cfg


def test_unhandled_exception_handler_logs_and_returns_500(
    mocker: MockerFixture,
) -> None:
    request = MagicMock()
    request.url.path = "/boom"
    request.method = "GET"
    exc = RuntimeError("explode")
    log_event = mocker.patch("app.application.Log.event")

    response = application._unhandled_exception_handler(request, exc)

    assert response.status_code == 500
    assert json.loads(response.body) == {"error": "Internal server error"}  # type: ignore
    log_event.assert_called_once_with(
        application.logger,
        Log.SYS_UNHANDLED_EXCEPTION,
        "Unhandled exception",
        exc_info=exc,
        exception_type="RuntimeError",
        endpoint="/boom",
        method="GET",
    )


def test_lifespan_logs_shutdown_reason_on_exit(use_config: Config, mocker: MockerFixture) -> None:
    log_event = mocker.patch("app.application.Log.event")
    mocker.patch("app.application._read_version", return_value="9.9.9")
    application._shutdown_reason = "graceful"

    async def _exercise() -> None:
        async with application._lifespan(MagicMock()):
            pass

    asyncio.run(_exercise())

    log_event.assert_any_call(
        application.logger,
        Log.SYS_APP_STOPPED,
        "Application stopped",
        shutdown_reason="graceful",
    )


def test_lifespan_defaults_to_graceful_shutdown_reason(use_config: Config, mocker: MockerFixture) -> None:
    importlib.reload(application)
    mocker.patch("app.application._read_version", return_value="9.9.9")
    log_event = mocker.patch("app.application.Log.event")

    async def _exercise() -> None:
        async with application._lifespan(MagicMock()):
            pass

    asyncio.run(_exercise())

    log_event.assert_any_call(
        application.logger,
        Log.SYS_APP_STOPPED,
        "Application stopped",
        shutdown_reason="graceful",
    )


def test_emit_app_started_logs_sys_app_started(use_config: Config, mocker: MockerFixture) -> None:
    mocker.patch("app.application._read_version", return_value="1.2.3")
    log_event = mocker.patch("app.application.Log.event")

    application._emit_app_started()

    log_event.assert_called_once_with(
        application.logger,
        Log.SYS_APP_STARTED,
        "Application started",
        version="1.2.3",
        config_path=mocker.ANY,
    )


def test_excepthook_logs_sys_app_crashed_for_uncaught_exception(
    mocker: MockerFixture,
) -> None:
    mocker.patch("app.application._read_version", return_value="9.9.9")
    log_event = mocker.patch("app.application.Log.event")
    previous_excepthook = sys.excepthook
    try:
        application._install_excepthook()
        try:
            raise RuntimeError("boom")
        except RuntimeError:
            sys.excepthook(*sys.exc_info())
    finally:
        sys.excepthook = previous_excepthook

    assert application._shutdown_reason == "crash"
    assert log_event.call_count == 1
    args, kwargs = log_event.call_args
    assert args[0] is application.logger
    assert args[1] is Log.SYS_APP_CRASHED
    assert args[2] == "Application crashed: uncaught exception"
    assert kwargs["shutdown_reason"] == "crash"
    assert kwargs["last_exception_type"] == "RuntimeError"
    assert kwargs["exc_info"] is not None


def test_create_fastapi_app_logs_sys_unhandled_exception_on_startup_failure(
    mocker: MockerFixture,
) -> None:
    mocker.patch("app.application.application_init")
    exc = RuntimeError("startup boom")
    mocker.patch("app.application.setup_fastapi", side_effect=exc)
    log_event = mocker.patch("app.application.Log.event")

    with pytest.raises(RuntimeError):
        application.create_fastapi_app()

    log_event.assert_called_once_with(
        application.logger,
        Log.SYS_UNHANDLED_EXCEPTION,
        "Unhandled exception during application startup",
        exc_info=exc,
        exception_type="RuntimeError",
    )


def test_signal_handler_sets_shutdown_reason_and_lifespan_logs_signal(
    use_config: Config, mocker: MockerFixture
) -> None:
    mocker.patch("app.application._read_version", return_value="9.9.9")
    log_event = mocker.patch("app.application.Log.event")
    application._shutdown_reason = "graceful"

    previous = signal.getsignal(signal.SIGTERM)
    try:
        application._install_signal_handlers()
        installed = signal.getsignal(signal.SIGTERM)
        assert callable(installed)
        installed(signal.SIGTERM, None)
    finally:
        signal.signal(signal.SIGTERM, previous)

    assert application._shutdown_reason == "signal:SIGTERM"

    async def _exercise() -> None:
        async with application._lifespan(MagicMock()):
            pass

    asyncio.run(_exercise())

    log_event.assert_any_call(
        application.logger,
        Log.SYS_APP_STOPPED,
        "Application stopped",
        shutdown_reason="signal:SIGTERM",
    )


def test_excepthook_skips_keyboard_interrupt(mocker: MockerFixture) -> None:
    log_event = mocker.patch("app.application.Log.event")
    previous_excepthook = sys.excepthook
    default_hook = mocker.patch("sys.__excepthook__")
    try:
        application._install_excepthook()
        try:
            raise KeyboardInterrupt()
        except KeyboardInterrupt:
            sys.excepthook(*sys.exc_info())
    finally:
        sys.excepthook = previous_excepthook

    log_event.assert_not_called()
    default_hook.assert_called_once()
