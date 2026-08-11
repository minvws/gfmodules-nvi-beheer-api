import json
import logging
import re
import time
import uuid
from contextvars import Token
from types import TracebackType
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.logging.context import (
    client_trace_id_var,
    endpoint_var,
    ip_var,
    method_var,
    request_id_var,
    x_gf_act_cn_var,
)
from app.logging.events import Log

REQUEST_ID_HEADER = "X-Request-ID"
CLIENT_TRACE_ID_HEADER = "X-Client-Trace-ID"
CLIENT_CN_HEADER = "x-gf-act-cn"

_SAFE_HEADER_VALUE = re.compile(r"[^a-zA-Z0-9\-_]")
_access_logger = logging.getLogger("app.access")
logger = logging.getLogger(__name__)


def _sanitize(value: str) -> str:
    return _SAFE_HEADER_VALUE.sub("", value)[:64]


class RequestContextVars:
    token_id: Token[str]
    token_ip: Token[str]
    token_trace: Token[str]
    token_endpoint: Token[str]
    token_method: Token[str]
    token_x_gf_act_cn: Token[str]

    def __init__(
        self,
        request: Request,
    ):
        self.request = request

    def __enter__(self) -> None:
        if "id" not in self.request.state:
            self.request.state["id"] = uuid.uuid4()
        request_id = self.request.state["id"]
        ip = self.request.client.host if self.request.client else "-"
        client_trace_id = _sanitize(self.request.headers.get(CLIENT_TRACE_ID_HEADER, "-"))
        client_cn_header = _sanitize(self.request.headers.get(CLIENT_CN_HEADER, "-"))

        self.token_id = request_id_var.set(request_id)
        self.token_ip = ip_var.set(ip)
        self.token_trace = client_trace_id_var.set(client_trace_id)
        self.token_endpoint = endpoint_var.set(self.request.url.path)
        self.token_method = method_var.set(self.request.method)
        self.token_x_gf_act_cn = x_gf_act_cn_var.set(client_cn_header)

    def __exit__(self, exc_type: type, exc_value: Exception, traceback: TracebackType) -> None:
        request_id_var.reset(self.token_id)
        ip_var.reset(self.token_ip)
        client_trace_id_var.reset(self.token_trace)
        endpoint_var.reset(self.token_endpoint)
        method_var.reset(self.token_method)
        x_gf_act_cn_var.reset(self.token_x_gf_act_cn)


def _get_router_path(request: Request) -> str:
    route = request.scope.get("route")
    if route and hasattr(route, "path"):
        return str(route.path)
    return "-"


async def _request_body(request: Request) -> str:
    body = await request.body()

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": body}

    request._receive = receive
    return body.decode("utf-8")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        with RequestContextVars(request):
            client_trace_id = _sanitize(request.headers.get(CLIENT_TRACE_ID_HEADER, "-"))
            body = await _request_body(request)
            response: Response | None = None
            start = time.perf_counter()
            try:
                response = await call_next(request)
                response.headers[REQUEST_ID_HEADER] = str(request.state["id"])
                if client_trace_id != "-":
                    response.headers[CLIENT_TRACE_ID_HEADER] = client_trace_id
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
