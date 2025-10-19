from typing import Literal, Optional

from pydantic import BaseModel, Field

from zion.agent.orchestrators_plugin import OrchestratorPluginConfig


class IncludeOpenAPIPath(BaseModel):
    path: str
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"]


class ServerEnvMetadata(BaseModel):
    """Server Environment Metadata."""

    host: str


class ServerMetadata(BaseModel):
    """Server Metadata."""

    staging: ServerEnvMetadata
    production: ServerEnvMetadata


class AgentConfigCustomAccessControl(BaseModel):
    users: Optional[list[str]] = None
    slack_channels: Optional[list[str]] = None


class AgentsConfig(BaseModel):
    ti_bot_dm: Optional[AgentConfigCustomAccessControl] = Field(None, alias="ti-bot-dm")
    ti_bot_level_zero: Optional[AgentConfigCustomAccessControl] = Field(
        None, alias="ti-bot-level-zero"
    )
    grabgpt_agent: Optional[dict] = Field({}, alias="grabgpt-agent")


class AccessControlConfig(BaseModel):
    agents: AgentsConfig


class ApiConfig(BaseModel):
    """API Configuration."""

    ref: str = ""  # GitLab YAML file path or local YAML file path
    include_paths: Optional[list[IncludeOpenAPIPath]]
    ignored_definition_keys: Optional[list[str]] = None
    server: ServerMetadata
    access_control: AccessControlConfig | None


class CommonOpenApiFields(BaseModel):
    description: Optional[str] = ""
    required: Optional[bool] = False


class SubTypeDetails(CommonOpenApiFields):
    properties_name: Optional[str]
    type: Literal["integer", "string", "boolean", "array", "object"]
    sub_type: Optional[Literal["", "integer", "string", "boolean", "array", "object"]]
    new_metadata_name: Optional[str]
    value: Optional[list[str]]


class PropertiesSpec(CommonOpenApiFields):
    metadata_name: str
    properties_name: str
    new_metadata_name: Optional[str] = ""
    type: Optional[Literal["", "integer", "string", "boolean", "array", "object"]]
    sub_type: Optional[Literal["", "integer", "string", "boolean", "array", "object"]]
    is_user_specified: bool
    value: Optional[list[str]]
    sub_type_details: Optional[list[SubTypeDetails]]


class RequestBodySchema(BaseModel):
    body_details: Optional[str] = ""
    properties_spec: Optional[list[PropertiesSpec]]


class ResponseBodySchema(RequestBodySchema):
    status_code: str
    response_description: str = ""


class BaseHeaderConfig(BaseModel):
    name: str
    value: str


class QueryParams(CommonOpenApiFields):
    name: str
    type: Literal["integer", "string", "boolean"]
    value: Optional[list[str]]


class UrlParams(QueryParams):
    pass


class PathConfig(BaseModel):
    path: str
    summary: str
    method: Literal["get", "post", "put"]
    query_params: Optional[list[QueryParams]]
    url_params: Optional[list[UrlParams]]
    custom_headers: Optional[list[BaseHeaderConfig]]
    request_body_schema: Optional[RequestBodySchema]
    response_body_schema: list[ResponseBodySchema]


class HttpPluginConfig(BaseModel):
    """HTTP Plugin Configuration."""

    service_name: str  # GitLab YAML file path or local YAML file path
    description: str
    server: ServerMetadata
    base_headers: list[BaseHeaderConfig]
    path_specification: list[PathConfig]


class OpenAPIPlugin(BaseModel):
    """OpenAPI Plugin Definition."""

    schema_version: str
    name_for_model: str
    name_for_human: str
    description_for_model: str
    description_for_human: str
    type: str = "openapi"
    owner: Optional[list[str]]
    api: ApiConfig
    http_plugin_detail: Optional[HttpPluginConfig]
    orchestrators_plugin: Optional[OrchestratorPluginConfig] = None


supported_openapi_20_versions = ["2.0"]
supported_openapi_3x_versions = ["3.0.0", "3.0.1", "3.0.2", "3.0.3", "3.1.0"]
supported_openapi_versions = (
    supported_openapi_20_versions + supported_openapi_3x_versions
)

unsupported_openapi_ref_error = NotImplementedError(
    "Only GitLab Blob URLs are supported now."
)

invalid_openapi_spec_error = ValueError(
    "The given YAML file is not a valid OpenAPI file."
)

unsupported_openapi_version_error = NotImplementedError(
    f"Only OpenAPI {', '.join(supported_openapi_versions)} are supported."
)
