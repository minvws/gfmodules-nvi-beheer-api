import json
import logging
import os
import signal
import sys
from contextlib import asynccontextmanager
from logging.config import dictConfig
from pathlib import Path
from types import TracebackType
from typing import Any, AsyncIterator

import uvicorn
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app import container
from app.config import (
    _ENVIRONMENT_CONFIG_PATH_NAME,
    _PATH,
    get_config,
)
from app.logging.config_builder import LogConfigBuilder
from app.logging.events import Log
from app.logging.middleware import RequestContextMiddleware
from app.middleware.stats import StatsdMiddleware
from app.routers.client import router as client_router
from app.routers.default import router as default_router
from app.routers.health import router as health_router
from app.routers.organization import router as organization_router
from app.routers.resolve import router as resolve_router

logger = logging.getLogger(__name__)

_shutdown_reason = "graceful"


async def request_validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    body = (await request.body()).decode(errors="replace")
    logger.warning(
        "Request validation failed method=%s path=%s body=%s errors=%s",
        request.method,
        request.url.path,
        body,
        exc.errors(),
    )
    return JSONResponse(status_code=422, content={"detail": jsonable_encoder(exc.errors())})


def get_uvicorn_params() -> dict[str, Any]:
    config = get_config()

    kwargs = {
        "host": config.uvicorn.host,
        "port": config.uvicorn.port,
        "reload": config.uvicorn.reload,
        "reload_delay": config.uvicorn.reload_delay,
        "reload_dirs": config.uvicorn.reload_dirs,
        "factory": True,
    }
    if (
        config.uvicorn.use_ssl
        and config.uvicorn.ssl_base_dir is not None
        and config.uvicorn.ssl_cert_file is not None
        and config.uvicorn.ssl_key_file is not None
    ):
        kwargs["ssl_keyfile"] = config.uvicorn.ssl_base_dir + "/" + config.uvicorn.ssl_key_file
        kwargs["ssl_certfile"] = config.uvicorn.ssl_base_dir + "/" + config.uvicorn.ssl_cert_file
    return kwargs


def run() -> None:
    uvicorn.run("app.application:create_fastapi_app", **get_uvicorn_params())


def application_init() -> None:
    setup_logging()
    _install_excepthook()
    _install_signal_handlers()


def create_fastapi_app() -> FastAPI:
    application_init()
    try:
        fastapi = setup_fastapi()
    except Exception as exc:
        Log.event(
            logger,
            Log.SYS_UNHANDLED_EXCEPTION,
            "Unhandled exception during application startup",
            exc_info=exc,
            exception_type=type(exc).__name__,
        )
        raise

    return fastapi


def setup_logging() -> None:
    config = get_config()
    loglevel = config.app.loglevel.upper()
    if loglevel not in logging.getLevelNamesMapping():
        raise ValueError(f"Invalid loglevel {loglevel}")

    log_config = LogConfigBuilder(
        loglevel=loglevel,
        logging_config=config.logging,
    ).build()
    dictConfig(log_config)


def _read_version() -> str:
    path = Path(__file__).parent.parent / "version.json"
    try:
        with open(path, "r") as fh:
            data = json.load(fh)
            return str(data.get("version", "unknown"))
    except (FileNotFoundError, json.JSONDecodeError):
        return "unknown"


def _install_excepthook() -> None:
    """Route uncaught exceptions through our own logging so the traceback stays in the
    debug stream only. Without this, Python prints the traceback to stderr and
    it leaks into stdout logs."""

    def _hook(
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_tb: TracebackType | None,
    ) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        global _shutdown_reason
        _shutdown_reason = "crash"
        Log.event(
            logger,
            Log.SYS_APP_CRASHED,
            "Application crashed: uncaught exception",
            shutdown_reason=_shutdown_reason,
            last_exception_type=exc_type.__name__,
            exc_info=(exc_type, exc_value, exc_tb),
        )

    sys.excepthook = _hook


def _install_signal_handlers() -> None:
    """Record the shutdown reason then delegate to the previously-installed
    handler (typically uvicorn's), so we don't disrupt graceful shutdown."""

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            previous = signal.getsignal(sig)
        except (ValueError, OSError):
            continue

        def _make_handler(signum: int, prev: Any) -> Any:
            def _handler(s: int, frame: Any) -> None:
                global _shutdown_reason
                _shutdown_reason = f"signal:{signal.Signals(signum).name}"
                if callable(prev):
                    prev(s, frame)

            return _handler

        try:
            signal.signal(sig, _make_handler(sig, previous))
        except (ValueError, OSError):
            pass


@asynccontextmanager
async def _lifespan(_: FastAPI) -> AsyncIterator[None]:
    global _shutdown_reason
    _emit_app_started()
    try:
        yield
    finally:
        if _shutdown_reason != "crash":
            Log.event(
                logger,
                Log.SYS_APP_STOPPED,
                "Application stopped",
                shutdown_reason=_shutdown_reason,
            )


def _emit_app_started() -> None:
    Log.event(
        logger,
        Log.SYS_APP_STARTED,
        "Application started",
        version=_read_version(),
        config_path=os.environ.get(_ENVIRONMENT_CONFIG_PATH_NAME, _PATH),
    )


def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    Log.event(
        logger,
        Log.SYS_UNHANDLED_EXCEPTION,
        "Unhandled exception",
        exc_info=exc,
        exception_type=type(exc).__name__,
        endpoint=request.url.path,
        method=request.method,
    )
    return JSONResponse(status_code=500, content={"error": "Internal server error"})


def setup_fastapi() -> FastAPI:
    config = get_config()

    fastapi = (
        FastAPI(
            docs_url=config.uvicorn.docs_url,
            redoc_url=config.uvicorn.redoc_url,
            title="NVI Beheer API",
            root_path=config.uvicorn.root_path,
            lifespan=_lifespan,
        )
        if config.uvicorn.swagger_enabled
        else FastAPI(docs_url=None, redoc_url=None, lifespan=_lifespan)
    )

    container.configure()

    routers = [default_router, health_router, organization_router, client_router, resolve_router]

    for router in routers:
        fastapi.include_router(router)

    fastapi.add_middleware(RequestContextMiddleware)
    fastapi.add_exception_handler(Exception, _unhandled_exception_handler)
    fastapi.exception_handler(RequestValidationError)(request_validation_exception_handler)

    if config.stats.enabled:
        fastapi.add_middleware(StatsdMiddleware, module_name=config.stats.module_name or "default")

    return fastapi
