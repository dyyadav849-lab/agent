from __future__ import annotations

import yaml
from langchain_core.tools import BaseTool
from pydantic import BaseModel

from zion.config import global_config
from zion.data.agent_plugin.constant import AGENT_OPENAPI_PLUGIN_TYPE
from zion.openapi.openapi_plugin import OpenAPIPlugin
from zion.openapi.util import (
    load_openapi_spec_from_http_plugin,
    load_remote_openapi_file,
)


class OpenAPIPluginToolSchema(BaseModel):
    """Schema for OpenAPIPluginTool."""


class OpenAPIPluginTool(BaseTool):
    """Tool for getting the OpenAPI spec for a plugin."""

    plugin: OpenAPIPlugin
    api_spec: str
    args_schema: type[OpenAPIPluginToolSchema] = OpenAPIPluginToolSchema

    @classmethod
    def from_plugin(cls: OpenAPIPluginTool, plugin: OpenAPIPlugin) -> OpenAPIPluginTool:
        server_url = plugin.api.server.staging.host
        if global_config.environment == "prd":
            server_url = plugin.api.server.production.host

        preset_ignored_definition_keys = [
            "protobufAny",  # Generate by protoc. Not a useful context for the LLM.
            "runtimeError",  # Generate by protoc. Not a useful context for the LLM.
        ]
        ignored_definition_keys = list(
            set(
                preset_ignored_definition_keys
                + (plugin.api.ignored_definition_keys or [])
            )
        )

        if plugin.api.ref != "":
            open_api_spec = load_remote_openapi_file(
                openapi_ref=plugin.api.ref,
                filter_paths=plugin.api.include_paths,
                ignored_definition_keys=ignored_definition_keys,
            )
            open_api_spec["servers"] = [{"url": server_url}]
        else:
            open_api_spec = (
                load_openapi_spec_from_http_plugin(plugin.http_plugin_detail)
                if plugin.http_plugin_detail is not None
                else {}
            )

        open_api_spec = yaml.dump(open_api_spec, indent=2)
        description = (
            f"Call this tool to get the OpenAPI spec (and usage guide) "
            f"for interacting with the {plugin.name_for_human} API. "
            f"You should only call this ONCE! What is the "
            f"{plugin.name_for_human} API useful for? "
            f"{plugin.description_for_model}"
        )
        api_spec = (
            f"Usage Guide:\n"
            f"1. {plugin.description_for_model}\n"
            f"2. You MUST ALWAYS include the `servers.url` and `basePath` in the URL if it present in the spec.\n\n"
            f"OpenAPI Spec:\n"
            f"{open_api_spec}"
        )

        return cls(
            name=plugin.name_for_model
            if plugin.type == AGENT_OPENAPI_PLUGIN_TYPE
            else f"open_api_spec_for_{plugin.name_for_model}",
            description=description,
            plugin=plugin,
            api_spec=api_spec,
        )

    def _run(
        self: OpenAPIPluginTool,
    ) -> str:
        """Use the tool."""
        return self.api_spec

    async def _arun(
        self: OpenAPIPluginTool,
    ) -> str:
        """Use the tool asynchronously."""
        return self.api_spec
