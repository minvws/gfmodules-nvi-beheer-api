from app.config import (
    Config,
    ConfigApp,
    ConfigDatabase,
    ConfigLogging,
    ConfigStats,
    ConfigTelemetry,
    ConfigUvicorn,
    LogLevel,
)


def get_test_config() -> Config:
    return Config(
        app=ConfigApp(
            loglevel=LogLevel.error,
        ),
        logging=ConfigLogging(
            app_path=None,
            siem_path=None,
            public_inspect_path=None,
            debug_path=None,
            include_traces=True,
            debug_logs_in_console=True,
        ),
        database=ConfigDatabase(
            dsn="sqlite:///:memory:",
            create_tables=True,
        ),
        telemetry=ConfigTelemetry(
            enabled=False,
            endpoint=None,
            service_name=None,
            tracer_name=None,
        ),
        stats=ConfigStats(enabled=False, host=None, port=None, module_name=None),
        uvicorn=ConfigUvicorn(
            docs_url="/docs",
            redoc_url="/redoc",
            swagger_enabled=True,
            ssl_base_dir="/ssl",
            ssl_cert_file="/file.cert",
            ssl_key_file="/file.key",
        ),
    )
