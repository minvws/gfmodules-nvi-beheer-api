import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

import gfmodules.logging as gflog
import uvicorn
from fastapi import FastAPI, Request, Security
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from gfmodules.logging.exceptions import log_unhandled_exception
from gfmodules.logging.middleware import RequestContextMiddleware, restore_request_context

from app import container
from app.config import (
    _ENVIRONMENT_CONFIG_PATH_NAME,
    _PATH,
    get_config,
)
from app.logging.events import ACT_CN, Log
from app.middleware.stats import StatsdMiddleware
from app.routers.client import router as client_router
from app.routers.default import router as default_router
from app.routers.health import router as health_router
from app.routers.organization import router as organization_router
from app.routers.resolve import router as resolve_router

logger = logging.getLogger(__name__)


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


def api_key_headers(document_gf_headers: bool) -> list[Any]:
    headers = []
    if document_gf_headers:
        headers = [
            "x-gf-act-cn",
        ]
    return [Security(APIKeyHeader(name=header, scheme_name=header, auto_error=False)) for header in headers]


def run() -> None:
    uvicorn.run("app.application:create_fastapi_app", **get_uvicorn_params())


def application_init() -> None:
    setup_logging()
    gflog.install_excepthook(logger)
    gflog.install_signal_handlers()


def create_fastapi_app() -> FastAPI:
    application_init()
    try:
        fastapi = setup_fastapi()
    except Exception as exc:
        gflog.emit(
            logger,
            Log.SYS_UNHANDLED_EXCEPTION,
            "Unhandled exception during application startup",
            fields={"exception_type": type(exc).__name__},
            exc_info=exc,
        )
        raise

    return fastapi


def setup_logging() -> None:
    config = get_config()
    gflog.configure(
        config=config.logging,
        loglevel=config.app.loglevel,
        catalogue=Log,
        extra_context_fields=(ACT_CN,),
    )


def _read_version() -> str:
    path = Path(__file__).parent.parent / "version.json"
    try:
        with open(path, "r") as fh:
            data = json.load(fh)
            return str(data.get("version", "unknown"))
    except (FileNotFoundError, json.JSONDecodeError):
        return "unknown"


@asynccontextmanager
async def _lifespan(_: FastAPI) -> AsyncIterator[None]:
    async with gflog.lifespan_logging(
        logger,
        version=_read_version(),
        config_path=os.environ.get(_ENVIRONMENT_CONFIG_PATH_NAME, _PATH),
    ):
        yield


@restore_request_context
def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    log_unhandled_exception(logger, request, exc)
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
            dependencies=api_key_headers(config.uvicorn.document_gf_headers),
        )
        if config.uvicorn.swagger_enabled
        else FastAPI(docs_url=None, redoc_url=None, lifespan=_lifespan)
    )

    container.configure()

    routers = [default_router, health_router, organization_router, client_router, resolve_router]

    for router in routers:
        fastapi.include_router(router)

    fastapi.add_exception_handler(Exception, _unhandled_exception_handler)
    fastapi.exception_handler(RequestValidationError)(request_validation_exception_handler)

    if config.stats.enabled:
        fastapi.add_middleware(StatsdMiddleware, module_name=config.stats.module_name or "default")

    fastapi.add_middleware(
        RequestContextMiddleware,
        correlation_id_expected=config.logging.correlation_id_expected,
        capture_body_methods=("POST", "PUT", "DELETE"),
        trust_forwarded_for=config.logging.trust_forwarded_for,
    )
    return fastapi
