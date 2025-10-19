import logging
import os
from configparser import ConfigParser, ExtendedInterpolation
from functools import lru_cache
from pathlib import Path

import typer
from pydantic_settings import BaseSettings

from app.core.log.logger import Logger


class AppConfig(BaseSettings):
    environment: str = "dev"
    server_base_url: str = ""

    # Database
    postgres_db_user: str = ""
    postgres_db_password: str = ""
    postgres_db_host: str = ""
    postgres_db_port: int = 0
    postgres_db_name: str = ""
    postgres_max_overflow: int = 0
    postgres_pool_size: int = 0
    postgres_pool_timeout: int = 0
    postgres_pool_recycle: int = 0

    # GrabGPT
    grabgpt_endpoint: str = ""
    grabgpt_api_key: str = ""
    grabgpt_openai_api_version: str = ""

    # LangSmith / LangChain
    langchain_endpoint: str = ""
    langchain_api_key: str = ""
    langchain_project: str = ""
    langchain_tracing_v2: str = ""

    # OTel settings (defaults)
    otel_python_logging_auto_instrumentation_enabled: str = ""
    otel_exporter_otlp_endpoint: str = "127.0.0.1:4317"
    otel_excluded_endpoints: str = ""

    # Logging: DEBUG, INFO, WARNING, ERROR, EXCEPTION
    log_level: str = ""

    # OIDC settings
    oidc_provider_wellknown_endpoint: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    oidc_scopes: str = ""

    # Session settings
    session_secret_key: str = ""

    # Datadog settings
    dd_statsd_socket_path: str = ""

    # Redis settings
    redis_host: str = ""
    redis_port: int = 6379

    # Auth settings
    auth_mode: str = ""
    auth_login_redirect: str = ""

    # Other settings
    knowledge_base_default_query_limit: int = 20

    # S3
    s3_bucket_name: str = ""

    # rag document header
    document_rag_secret_key: str = ""



    def set_environment_variables(self) -> None:
        """Set environment variables from config."""

        # Setting environment variables required for LangSmith
        os.environ["LANGCHAIN_ENDPOINT"] = self.langchain_endpoint
        os.environ["LANGCHAIN_API_KEY"] = self.langchain_api_key
        os.environ["LANGCHAIN_PROJECT"] = self.langchain_project
        os.environ["LANGCHAIN_TRACING_V2"] = self.langchain_tracing_v2
        os.environ["OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED"] = (
            self.otel_python_logging_auto_instrumentation_enabled
        )
        os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = self.otel_exporter_otlp_endpoint


@lru_cache
def get_config(
    environment: str = os.environ.get("ENVIRONMENT", "dev"),
    secret_init_path: str = os.environ.get("SECRET_INI_PATH", "configs/secret.ini"),
) -> AppConfig:
    # parser will be used to contain the main overall rendered config
    parser = ConfigParser(interpolation=ExtendedInterpolation())

    # read raw secret value first
    secret_parser = ConfigParser(interpolation=ExtendedInterpolation())
    _ = secret_parser.read(
        [Path(secret_init_path)],
        encoding="utf-8",
    )

    # special character $ must be escaped for use in extended interpolation later with overall config
    secret_sections = secret_parser.sections()
    for section in secret_sections:
        section_items = dict(secret_parser.items(section, raw=True))
        parser.add_section(section)
        for key, value in section_items.items():
            safe_value = value.replace("$", "$$")
            # we set the safe secret value for later extended interpolation reference
            parser.set(section, key, safe_value)

    # read and render the main config
    config_paths = parser.read(
        [Path("configs/" + environment + ".ini")],
        encoding="utf-8",
    )

    # at this stage we haven't get the env var setup, so we cant use the global logger
    logger = Logger("config", logging.INFO)
    logger.info("Reading config from paths: %s", config_paths)

    output_dict = {}

    sections = parser.sections()
    for section in sections:
        output_dict.update(dict(parser.items(section)))

    return AppConfig(**output_dict)


# initialize the app config
app_config = get_config()
app_config.set_environment_variables()

log_level = (
    getattr(logging, app_config.log_level)
    if hasattr(logging, app_config.log_level)
    else logging.INFO
)
logger = Logger("app", log_level)


def main(key: str) -> None:
    """Print config value of specified key."""
    typer.echo(app_config.dict().get(key))


if __name__ == "__main__":
    typer.run(main)
