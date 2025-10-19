from typing import Literal, Optional

from pydantic import BaseModel, Field


# Apply this to ensure the new field name can be called (use for alias)
class ConfiguredBaseModel(BaseModel):
    class Config:
        populate_by_name = True


class DefaultSchema(BaseModel):
    type: Optional[str] = "string"
    enum: Optional[list[str]] = None


class ParameterSchema(BaseModel):
    name: str
    in_: Optional[str] = Field(default="", alias="in")
    description: Optional[str] = ""
    required: Optional[bool] = False
    schema_: Optional[DefaultSchema] = Field(default={}, alias="schema")


class Paramters(BaseModel):
    parameters: dict[str, ParameterSchema]


class PropertiesSchema(BaseModel):
    type: Optional[Literal["integer", "string", "boolean", "array", "object"]] = None
    description: str = ""
    enum: Optional[list[str]] = None
    items: Optional["PropertiesSchema"] = None
    properties: Optional[dict[str, "PropertiesSchema"]] = None


class RequestResponseDetails(BaseModel):
    type: str = "object"
    description: str = ""
    required: Optional[list[str]] = None
    properties: Optional[dict[str, PropertiesSchema]] = None


class ApplicationJsonSchema(ConfiguredBaseModel):
    schema_: Optional[RequestResponseDetails] = Field(alias="schema")


class ContentSchema(ConfiguredBaseModel):
    application_json: Optional[ApplicationJsonSchema] = Field(alias="application/json")


class RequestScheme(BaseModel):
    required: bool = True
    content: Optional[ContentSchema]


class ResponseScheme(BaseModel):
    description: str = ""
    content: Optional[ContentSchema]


class PathDetailsSchema(BaseModel):
    summary: str
    parameters: Optional[list[ParameterSchema]]
    requestBody: Optional[RequestScheme]  # noqa: N815
    responses: dict[str, ResponseScheme]


class ServerConfig(BaseModel):
    url: str


class InfoConfig(BaseModel):
    """Info Configuration."""

    title: str
    version: str = "1.0.0"
    description: str


class HttpPlugin(BaseModel):
    """Http Plugin Definition."""

    openapi: str
    info: InfoConfig
    servers: list[ServerConfig]
    components: Optional[Paramters]
    paths: dict[str, dict[str, PathDetailsSchema]]
