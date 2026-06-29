import logging
import re
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.logging.context import (
    client_trace_id_var,
    endpoint_var,
    ip_var,
    method_var,
    request_id_var,
)
from app.logging.events import Log

REQUEST_ID_HEADER = "X-Request-ID"
CLIENT_TRACE_ID_HEADER = "X-Client-Trace-ID"

_SAFE_HEADER_VALUE = re.compile(r"[^a-zA-Z0-9\-_]")
_access_logger = logging.getLogger("app.access")


def _sanitize(value: str) -> str:
    return _SAFE_HEADER_VALUE.sub("", value)[:64]


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = str(uuid.uuid4())
        ip = request.client.host if request.client else "-"
        client_trace_id = _sanitize(request.headers.get(CLIENT_TRACE_ID_HEADER, "-"))

        token_id = request_id_var.set(request_id)
        token_ip = ip_var.set(ip)
        token_trace = client_trace_id_var.set(client_trace_id)
        token_endpoint = endpoint_var.set(request.url.path)
        token_method = method_var.set(request.method)
        response: Response | None = None
        start = time.perf_counter()
        try:
            response = await call_next(request)
            response.headers[REQUEST_ID_HEADER] = request_id
            if client_trace_id != "-":
                response.headers[CLIENT_TRACE_ID_HEADER] = client_trace_id
            return response
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000)
            Log.event(
                _access_logger,
                Log.ACCESS_REQUEST,
                "access",
                status_code=response.status_code if response is not None else None,
                duration_ms=duration_ms,
            )
            request_id_var.reset(token_id)
            ip_var.reset(token_ip)
            client_trace_id_var.reset(token_trace)
            endpoint_var.reset(token_endpoint)
            method_var.reset(token_method)
