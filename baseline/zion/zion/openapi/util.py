from __future__ import annotations

from typing import Any

from zion.config import global_config
from zion.openapi.http_plugin import HttpPlugin, InfoConfig, Paramters, ServerConfig
from zion.openapi.http_plugin_to_openapi import (
    convert_base_header_to_opanapi_spec_format,
    convert_path_specification_to_opanapi_spec_format,
)
from zion.openapi.openapi3x import reduce_openapi_3x_spec
from zion.openapi.openapi20 import reduce_openapi_20_spec
from zion.openapi.openapi_plugin import (
    HttpPluginConfig,
    IncludeOpenAPIPath,
    OpenAPIPlugin,
    invalid_openapi_spec_error,
    supported_openapi_3x_versions,
    supported_openapi_20_versions,
    supported_openapi_versions,
    unsupported_openapi_ref_error,
    unsupported_openapi_version_error,
)
from zion.util.gitlab import is_gitlab_blob_url, load_gitlab_file_in_dict


def load_remote_openapi_file(
    openapi_ref: str,
    filter_paths: list[IncludeOpenAPIPath] | None = None,
    ignored_definition_keys: list[str] | None = None,
) -> dict[str, Any]:
    """Load a OpneAPI (Swagger) specification from the given URL."""
    if filter_paths is None:
        filter_paths = []
    if ignored_definition_keys is None:
        ignored_definition_keys = []

    check_supported_openapi_url(openapi_ref)

    raw_spec = load_gitlab_file_in_dict(openapi_ref)

    if raw_spec.get("swagger") in supported_openapi_20_versions:
        return reduce_openapi_20_spec(raw_spec, filter_paths, ignored_definition_keys)

    if raw_spec.get("openapi") in supported_openapi_3x_versions:
        return reduce_openapi_3x_spec(raw_spec, filter_paths, ignored_definition_keys)

    raise unsupported_openapi_version_error


def check_supported_openapi_url(openapi_url: str) -> None:
    """Check if the given URL is a supported OpenAPI URL."""
    if not is_gitlab_blob_url(openapi_url):
        raise unsupported_openapi_ref_error


def check_valid_openapi_version(openapi_spec: dict[str, Any]) -> bool:
    """Check if the given OpenAPI spec is a valid version."""
    openapi_version = openapi_spec.get("swagger", openapi_spec.get("openapi"))

    if openapi_version is None:
        raise invalid_openapi_spec_error

    if openapi_version not in supported_openapi_versions:
        raise unsupported_openapi_version_error

    return False


def check_http_plugin_data(plugin_info: OpenAPIPlugin) -> None:
    """Check if the HTTP plugin data provided is a supported."""
    load_openapi_spec_from_http_plugin(
        plugin_info.http_plugin_detail
    ) if plugin_info.http_plugin_detail is not None else {}


def load_openapi_spec_from_http_plugin(
    http_plugin: HttpPluginConfig,
) -> HttpPlugin:
    """Load a OpneAPI (Swagger) specification from the http plugin json."""

    # Initialize an empty dictionary for component and path parameters
    component_parameters = {}
    path_parameters = {}

    convert_base_header_to_opanapi_spec_format(
        component_parameters, http_plugin.base_headers
    )
    convert_path_specification_to_opanapi_spec_format(
        path_parameters, http_plugin.path_specification
    )

    http_plugin_data = HttpPlugin(
        openapi="3.0.0",
        info=InfoConfig(
            title=http_plugin.service_name, description=http_plugin.description
        ),
        servers=[
            ServerConfig(
                url=http_plugin.server.production.host
                if global_config.environment == "prd"
                else http_plugin.server.staging.host
            )
        ],
        components=Paramters(parameters=component_parameters),
        paths=path_parameters,
    )

    return http_plugin_data.dict(exclude_none=True, by_alias=True)
