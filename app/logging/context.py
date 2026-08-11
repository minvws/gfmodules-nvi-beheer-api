from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
ip_var: ContextVar[str] = ContextVar("ip", default="-")
client_trace_id_var: ContextVar[str] = ContextVar("client_trace_id", default="-")
endpoint_var: ContextVar[str] = ContextVar("endpoint", default="-")
method_var: ContextVar[str] = ContextVar("method", default="-")
x_gf_act_cn_var: ContextVar[str] = ContextVar("gf-act-cn", default="-")
