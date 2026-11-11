import traceback
from collections.abc import Generator
from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

from app.config import (
    Config,
    ConfigApp,
    ConfigDatabase,
    ConfigError,
    ConfigLogging,
    ConfigStats,
    ConfigTelemetry,
    ConfigUvicorn,
    LogLevel,
    get_config,
    read_ini_file,
    reset_config,
)


def get_test_config() -> Config:
    return Config(
        app=ConfigApp(
            loglevel=LogLevel.error,
        ),
        logging=ConfigLogging(
            syslog_path=None,
            application_id="nvi-beheer-api",
            include_traces=True,
            console_streams=["debug"],
        ),
        database=ConfigDatabase(
            dsn=SecretStr("sqlite:///:memory:"),
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


# Kept short: pydantic shortens long values in its messages, which would hide the leak these tests guard against.
SECRET = "hunter2"
LEAKY_DATABASE_SECTION = f"dns = postgresql://u:{SECRET}@db/n"


@pytest.fixture
def uncached_config() -> Generator[None, None, None]:
    reset_config()
    yield
    reset_config()


def write_config(tmp_path: Path, database_section: str) -> str:
    path = tmp_path / "app.conf"
    path.write_text(f"[database]\n{database_section}\n")
    return str(path)


def load_invalid_config(tmp_path: Path, database_section: str) -> ConfigError:
    path = write_config(tmp_path, database_section)
    with pytest.raises(ConfigError) as exc_info:
        get_config(path)
    return exc_info.value


def test_pydantic_error_for_misspelled_dsn_contains_the_secret(tmp_path: Path) -> None:
    """Precondition for the tests below: without sanitizing, the misspelled key's value (the DSN) is in the error."""
    ini_data = read_ini_file(write_config(tmp_path, LEAKY_DATABASE_SECTION))

    with pytest.raises(ValidationError) as exc_info:
        Config.model_validate(ini_data)

    assert SECRET in str(exc_info.value)


@pytest.mark.usefixtures("uncached_config")
def test_invalid_config_error_never_contains_values(tmp_path: Path) -> None:
    error = load_invalid_config(tmp_path, LEAKY_DATABASE_SECTION)

    assert "database.dsn: Field required" in str(error)
    assert SECRET not in "".join(traceback.format_exception(error))


@pytest.mark.usefixtures("uncached_config")
def test_invalid_config_error_names_field_and_reason(tmp_path: Path) -> None:
    error = load_invalid_config(tmp_path, f"dsn = postgresql://u:{SECRET}@db/n\npool_size = lots")

    assert "database.pool_size: Input should be a valid integer" in str(error)
    assert "lots" not in str(error)


@pytest.mark.usefixtures("uncached_config")
def test_invalid_config_error_lists_every_failing_field(tmp_path: Path) -> None:
    error = load_invalid_config(tmp_path, LEAKY_DATABASE_SECTION)

    for field in ("app", "database.dsn", "telemetry", "stats", "uvicorn"):
        assert f"{field}: Field required" in str(error)


def test_the_example_config_reads_the_logging_streams() -> None:
    logging = ConfigLogging.model_validate(read_ini_file("app.conf.example")["logging"])

    assert logging.syslog_streams == ["app", "siem", "public_inspect"]
    assert logging.console_streams == ["debug"]
