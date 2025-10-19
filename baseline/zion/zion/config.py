import logging
import os
from configparser import ConfigParser, ExtendedInterpolation
from functools import lru_cache
from pathlib import Path

import typer
from pydantic import BaseModel
from pydantic_settings import BaseSettings

from zion.stats.datadog import DatadogClient
from zion.util.log.logger import Logger

# config logger
log_level = (
    logging.DEBUG if os.environ.get("ENVIRONMENT", "dev") == "dev" else logging.WARNING
)
logger = Logger("zion", log_level)


class AgentProfile(BaseModel):
    profile_name: str
    secret_key: str
    langchain_project: str = ""


class AppConfig(BaseSettings):
    environment: str = "dev"
    domain: str = ""

    # logging
    log_console: bool = True
    log_file: str = ""

    # Database
    mysql_db_user: str = ""
    mysql_db_password: str = ""
    mysql_db_host: str = ""
    mysql_db_port: int = 3306
    mysql_db_name: str = "zion"

    # Gitlab
    grab_gitlab_access_token: str = ""

    # OpenAI
    openai_endpoint: str = ""
    openai_api_key: str = ""

    # AIHome BE
    private_openai_endpoint: str = ""
    aihome_openai_api_key: str = ""

    # Agent
    agent_log_verbose: bool = False

    # LangSmith / LangChain
    langchain_endpoint: str = ""
    langchain_api_key: str = ""
    langsmith_handle_prefix: str = ""

    # Kendra
    kendra_index_id: str = ""
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_session_token: str = ""

    # For Glean
    glean_base_url: str = ""
    glean_bearer_token: str = ""

    # For Grab Concedo
    concedo_private_key: str = ""
    concedo_client_id: str = ""
    concedo_app_id: str = ""
    concedo_public_key_id: str = ""
    helix_concedo_client_id: str = ""
    concedo_client_secret: str = ""

    # For Helix
    helix_base_url: str = ""

    # For Confluence
    confluence_base_url: str = ""
    confluence_username: str = ""
    confluence_password: str = ""

    # For Jira
    jira_base_url: str = ""
    jira_username: str = ""
    jira_password: str = ""

    # For Knowledge Base Service
    knowledge_base_service_base_url: str = ""

    # For Hades KB Service
    hades_kb_service_base_url: str = ""
    hades_document_rag_secret_key: str = ""

    # For Presto
    presto_username: str = ""
    presto_password: str = ""

    # For Google Service Account
    google_project_id: str = ""
    google_private_key_id: str = ""
    google_private_key: str = ""
    google_client_email: str = ""
    google_client_id: str = ""
    google_client_x509_cert_url: str = ""

    # For Token Optimization
    langchain_token_opt_project: str = ""

    # For kibana logs retrieval
    kibana_username: str = ""
    kibana_password: str = ""
    kibana_base_url: str = ""

    # OTel settings (defaults)
    otel_python_logging_auto_instrumentation_enabled: str = ""
    otel_exporter_otlp_endpoint: str = "127.0.0.1:4317"
    otel_excluded_endpoints: str = ""

    # Datadog settings
    dd_statsd_socket_path: str = ""
    datadog_app_key: str = ""
    datadog_api_key: str = ""
    datadog_site: str = "datadoghq.com"

    # Gitlab settings
    gitlab_api_token: str = ""

    # For Fernet encryption/ decryption (cryptography)
    fernet_key: str = ""

    # SourceGraph settings
    sourcegraph_access_token: str = ""
    sourcegraph_host: str = ""
    # enable/disable certificate
    sourcegraph_verify_certificate: bool = True
    sourcegraph_query_gitlab_host: str = ""

    # Langsmith eval prompts
    request_system_prompt: str = ""
    response_system_prompt: str = ""

    # MCP
    mcp_gitlab_mr_creation_template: str = ""

    # For TI Support
    ti_support_base_url: str = ""

    # Evaluation settings
    evaluation_batch_size: int = 5  # Number of samples to insert in each batch

    agent_profiles: dict[str, AgentProfile]


@lru_cache
def get_config(
    environment: str = os.environ.get("ENVIRONMENT", "dev"),
    secret_init_path: str = os.environ.get("SECRET_INI_PATH", "configs/secret.ini"),
) -> AppConfig:
    parser = ConfigParser(interpolation=ExtendedInterpolation())
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
    logger.info("Reading config from paths: %s", config_paths)

    output_dict = {}
    output_dict["agent_profiles"] = {}

    sections = parser.sections()
    for section in sections:
        logger.info("Reading section: %s", section)

        # Strip quotes around of values as ConfigParser parse the values with quotes
        # when ExtendedInterpolation is in used
        for key in parser[section]:
            value = parser[section][key]
            safe_value = value.replace("$", "$$").strip('"')
            parser[section][key] = safe_value

        if section.startswith("AGENT_PROFILE."):
            agent_profile = dict(parser.items(section))
            output_dict["agent_profiles"][agent_profile["profile_name"]] = agent_profile
        elif section == "CONFIG":
            output_dict.update(dict(parser.items(section)))

    return AppConfig(**output_dict)


def set_environ_vars_from_config() -> None:
    """Set environment variables from config."""

    if is_langsmith_enabled():
        # These env variables are required for LangChain tracing
        # We set the environment here in order for tracing_v2_enabled to work
        os.environ["LANGCHAIN_ENDPOINT"] = global_config.langchain_endpoint
        os.environ["LANGCHAIN_API_KEY"] = global_config.langchain_api_key

        # Always enable tracing when LangSmith is used, this is prerequisite of using the LangSmith Feedback API

        os.environ["LANGCHAIN_TRACING_V2"] = "true"


def is_langsmith_enabled() -> bool:
    return (
        global_config.langchain_endpoint != "" and global_config.langchain_api_key != ""
    )


# initialize the app config
global_config = get_config()
logger.debug("config", tags={"config": global_config.dict()})

set_environ_vars_from_config()


# Initialize the statsd client
statsd = DatadogClient(
    options={
        "api_key": global_config.datadog_api_key,
        "app_key": global_config.datadog_app_key,
        "statsd_socket_path": global_config.dd_statsd_socket_path,
    },
    env=global_config.environment,
    appname="zion",
)


def main(key: str) -> None:
    """Print config value of specified key."""
    typer.echo(global_config.dict().get(key))


if __name__ == "__main__":
    typer.run(main)
