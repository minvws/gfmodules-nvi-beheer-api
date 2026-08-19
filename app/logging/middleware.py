import json
import logging
import re
import time
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.logging.context import (
    CLIENT_CN_HEADER,
    CLIENT_TRACE_ID_HEADER,
    CORRELATION_ID_HEADER,
    REQUEST_ID_HEADER,
    UNSET,
    client_trace_id_var,
    correlation_id_var,
    endpoint_var,
    ip_var,
    method_var,
    request_id_var,
    x_gf_act_cn_var,
)
from app.logging.events import Log

_SAFE_HEADER_VALUE = re.compile(r"[^a-zA-Z0-9\-_]")
_access_logger = logging.getLogger("app.access")
logger = logging.getLogger(__name__)


def _sanitize(value: str) -> str:
    return _SAFE_HEADER_VALUE.sub("", value)[:64] or UNSET


@dataclass(frozen=True)
class RequestContext:
    request_id: str
    ip: str
    client_trace_id: str
    correlation_id: str
    endpoint: str
    method: str
    x_gf_act_cn: str

    @classmethod
    def from_request(cls, request: Request) -> "RequestContext":
        # An upstream may already have stamped this request; reuse its id if so.
        if "id" not in request.state:
            request.state["id"] = uuid.uuid4()
        return cls(
            request_id=str(request.state["id"]),
            ip=request.client.host if request.client else UNSET,
            client_trace_id=_sanitize(request.headers.get(CLIENT_TRACE_ID_HEADER, UNSET)),
            correlation_id=_sanitize(request.headers.get(CORRELATION_ID_HEADER, UNSET)),
            endpoint=request.url.path,
            method=request.method,
            x_gf_act_cn=_sanitize(request.headers.get(CLIENT_CN_HEADER, UNSET)),
        )

    def apply_to(self, response: Response) -> None:
        response.headers[REQUEST_ID_HEADER] = self.request_id
        if self.client_trace_id != UNSET:
            response.headers[CLIENT_TRACE_ID_HEADER] = self.client_trace_id
        if self.correlation_id != UNSET:
            response.headers[CORRELATION_ID_HEADER] = self.correlation_id


_CONTEXT_VARS: tuple[tuple[str, ContextVar[str]], ...] = (
    ("request_id", request_id_var),
    ("ip", ip_var),
    ("client_trace_id", client_trace_id_var),
    ("correlation_id", correlation_id_var),
    ("endpoint", endpoint_var),
    ("method", method_var),
    ("x_gf_act_cn", x_gf_act_cn_var),
)


@contextmanager
def _bind(context: RequestContext) -> Generator[None]:
    tokens = [(var, var.set(getattr(context, name))) for name, var in _CONTEXT_VARS]
    try:
        yield
    finally:
        for var, token in reversed(tokens):
            var.reset(token)


def _get_router_path(request: Request) -> str:
    route = request.scope.get("route")
    if route and hasattr(route, "path"):
        return str(route.path)
    return UNSET


async def _request_body(request: Request) -> str:
    body = await request.body()

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": body}

    request._receive = receive
    return body.decode("utf-8")


class RequestContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, correlation_id_expected: bool = False) -> None:
        super().__init__(app)
        self.correlation_id_expected = correlation_id_expected

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        context = RequestContext.from_request(request)

        with _bind(context):
            if self.correlation_id_expected and context.correlation_id == UNSET:
                Log.event(
                    logger,
                    Log.SYS_MISSING_CORRELATION_ID,
                    f"Request arrived without {CORRELATION_ID_HEADER}",
                    endpoint=context.endpoint,
                    method=context.method,
                )
            body = await _request_body(request)
            response: Response | None = None
            start = time.perf_counter()
            try:
                response = await call_next(request)
                context.apply_to(response)
                return response
            finally:
                duration_ms = round((time.perf_counter() - start) * 1000)
                args: dict[str, Any] = {
                    "status_code": response.status_code if response is not None else None,
                    "duration_ms": duration_ms,
                }
                if request.method in ["PUT", "POST", "DELETE"]:
                    try:
                        args["body"] = json.loads(body)
                    except json.JSONDecodeError as e:
                        logger.debug(e.msg)
                        args["body"] = str(body)
                Log.event(
                    logger=_access_logger,
                    event=Log.ACCESS_REQUEST,
                    message="access",
                    event_id=Log.access_event_id.get((request.method, _get_router_path(request))),
                    **args,
                )
