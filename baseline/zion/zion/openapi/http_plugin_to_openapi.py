from __future__ import annotations

import json
import re
from typing import Any, Union
from urllib.parse import parse_qs, urlparse

from zion.openapi.constant import (
    PARAMETERS_SCHEMA_IN_HEADER,
    PARAMETERS_SCHEMA_IN_QUERY,
    PARAMETERS_SCHEMA_IN_URL,
)
from zion.openapi.http_plugin import (
    ApplicationJsonSchema,
    ContentSchema,
    DefaultSchema,
    ParameterSchema,
    PathDetailsSchema,
    PropertiesSchema,
    RequestResponseDetails,
    RequestScheme,
    ResponseScheme,
)
from zion.openapi.openapi_plugin import (
    BaseHeaderConfig,
    PathConfig,
    PropertiesSpec,
    QueryParams,
    RequestBodySchema,
    ResponseBodySchema,
    SubTypeDetails,
    UrlParams,
)


def create_parameter_schema(
    data_schema: BaseHeaderConfig | UrlParams | QueryParams, type_: str
) -> ParameterSchema:
    """
    Create an OpenAPI spec parameters data.

    This function takes a data schema and a type string, and returns a ParameterSchema object
    that represents the parameters of an OpenAPI specification.
    """
    secret_name = data_schema.name
    if type_ == PARAMETERS_SCHEMA_IN_HEADER:
        valid_secret_key, secret_name = check_secret_prefix_and_get_secret_name(
            secret_name
        )
        if not valid_secret_key:
            err_message = "The secret header key must be in {{SECRET:keyName}} format."
            raise ValueError(err_message)

    header_schema = ParameterSchema(
        name=secret_name,
        description=data_schema.description
        if hasattr(data_schema, "description")
        else None,
    )

    schema = DefaultSchema(
        type=data_schema.type if hasattr(data_schema, "type") else "string",
        enum=data_schema.value
        if data_schema.value and isinstance(data_schema.value, list)
        else [data_schema.value]
        if data_schema.value
        else None,
    )
    header_schema.required = (
        data_schema.required if type_ == PARAMETERS_SCHEMA_IN_QUERY else True
    )
    header_schema.in_ = type_
    header_schema.schema_ = schema

    return header_schema


def create_path_parameter_schema(
    custom_headers: list[BaseHeaderConfig],
    url_params: list[UrlParams],
    query_params: list[QueryParams],
    path: str,
) -> list[ParameterSchema]:
    """
    Create a list of OpenAPI spec path parameter schemas.

    This function takes lists of custom headers, URL parameters, and query parameters,
    and returns a list of ParameterSchema objects that represent the parameters section
    of an OpenAPI specification.
    """
    # Parse the URL
    parsed_url = urlparse(path)

    parameters: list[ParameterSchema] = []

    for custom_header in custom_headers:
        custom_header_schema = create_parameter_schema(
            custom_header, PARAMETERS_SCHEMA_IN_HEADER
        )
        parameters.append(custom_header_schema)

    # Convert the url_params list to a dictionary
    url_param_list = create_param_list(url_params)
    url_params_in_path = extract_url_param(parsed_url.path)
    for url_param_in_path in url_params_in_path:
        # Check if url_param_in_path exists in url_params
        url_param = url_param_list.get(url_param_in_path)
        if not url_param:
            err_message = f"No Url Path Params found for param name {url_param_in_path}"
            raise ValueError(err_message)
        url_param_schema = create_parameter_schema(url_param, PARAMETERS_SCHEMA_IN_URL)
        parameters.append(url_param_schema)

    # Convert the query_params list to a dictionary
    query_param_list = create_param_list(query_params)
    query_params_in_path = extract_query_param(parsed_url.query)
    for key, value in query_params_in_path.items():
        if re.match(parameter_pattern, key):
            # Remove the pattern from the value
            new_key = key.replace("{{", "").replace("}}", "")
            query_param = query_param_list.get(new_key)
            if not query_param:
                err_message = f"No Query Params found for param name {new_key}"
                raise ValueError(err_message)
            query_param_schema = create_parameter_schema(
                query_param, PARAMETERS_SCHEMA_IN_QUERY
            )
            parameters.append(query_param_schema)
        else:
            schema = DefaultSchema(
                type="string",
                enum=value if value else None,
            )
            existing_query_param = ParameterSchema(
                name=key,
                required=True,
            )
            existing_query_param.in_ = PARAMETERS_SCHEMA_IN_QUERY
            existing_query_param.schema_ = schema
            parameters.append(existing_query_param)

    return parameters


def create_properties_schema(
    data_schema: PropertiesSpec | SubTypeDetails,
    properties_spec_list: dict[Any, PropertiesSpec],
) -> PropertiesSchema:
    """
    Create an OpenAPI spec properties schema.

    This function takes a data schema (which can be either a PropertiesSpec or SubTypeDetails instance)
    and a dictionary of properties specifications, and returns a PropertiesSchema object
    that represents the properties section of an OpenAPI specification.
    """
    properties_schema = PropertiesSchema(
        type=data_schema.type if data_schema.type != "" else "string",
        description=data_schema.description,
    )

    # Logic for PropertiesSpec class
    if isinstance(data_schema, PropertiesSpec):
        create_properties_schema_for_properties_spec(
            data_schema, properties_spec_list, properties_schema
        )

    # Logic for SubTypeDetails class
    if isinstance(data_schema, SubTypeDetails):
        create_properties_schema_for_sub_type_details(
            data_schema, properties_spec_list, properties_schema
        )

    if not data_schema.sub_type and data_schema.value:
        properties_schema.enum = data_schema.value

    return properties_schema


def create_properties_list(
    sub_type_details: list[SubTypeDetails],
    properties_spec_list: dict[Any, PropertiesSpec],
) -> dict[str, PropertiesSchema]:
    """
    Create a dictionary of OpenAPI spec properties schemas.

    This function takes a list of SubTypeDetails and a dictionary of properties specifications,
    and returns a dictionary where each key-value pair represents a property in an OpenAPI specification.
    The key is the property name, and the value is a PropertiesSchema object.
    """
    return {
        sub_type_detail.properties_name: create_properties_schema(
            sub_type_detail, properties_spec_list
        )
        for sub_type_detail in sub_type_details
    }


def create_properties_schema_for_properties_spec(
    data_schema: PropertiesSpec,
    properties_spec_list: dict[Any, PropertiesSpec],
    properties_schema: PropertiesSchema,
) -> None:
    """
    Modify a PropertiesSchema object based on a given PropertiesSpec instance and a list of property specifications.

    This function takes a PropertiesSpec instance, a dictionary of property specifications,
    and a PropertiesSchema instance. It modifies the PropertiesSchema instance based on the
    data in the PropertiesSpec instance and the property specifications.

    Here are the possible scenario for PropertiesSpec:
        1.Type == "object" -> For this case, sub_type will be empty, but sub_type_details will be used to store object Property (SubTypeDetails)
        2. Type == "array" -> For this case, need to refer to it sub_type
            - If sub_type == "object", sub_type_details will be used to store object Property (SubTypeDetails)
            - If sub_type == "array", sub_type_details will be empty, but need to refer new_metadata_name to retrieve the following Property
            - else, value is optional
    """
    if data_schema.type == "object":
        properties_schema.properties = create_properties_list(
            data_schema.sub_type_details, properties_spec_list
        )

    if data_schema.type == "array":
        if data_schema.sub_type == "object":
            properties_schema.items = PropertiesSchema(
                type=data_schema.sub_type,
                properties=create_properties_list(
                    data_schema.sub_type_details, properties_spec_list
                ),
            )
        elif data_schema.sub_type == "array":
            specific_properties = get_specific_properties_spec_by_metadata(
                properties_spec_list, data_schema.new_metadata_name
            )
            properties_schema.items = create_properties_schema(
                specific_properties, properties_spec_list
            )
        else:
            properties_schema.items = PropertiesSchema(
                type=data_schema.sub_type if data_schema.sub_type != "" else "string",
                enum=data_schema.value,
            )


def create_properties_schema_for_sub_type_details(
    data_schema: SubTypeDetails,
    properties_spec_list: dict[Any, PropertiesSpec],
    properties_schema: PropertiesSchema,
) -> None:
    """
    Modify a PropertiesSchema object based on a given SubTypeDetails.

    This function takes a SubTypeDetails instance, a dictionary of property specifications,
    and a PropertiesSchema instance. It modifies the PropertiesSchema instance based on the
    data in the SubTypeDetails instance and the property specifications.

    Here are the possible scenario for SubTypeDetails:
        1.Type == "object" -> For this case, need to refer new_metadata_name to retrieve the following Property
        2. Type == "array" -> For this case, need to refer to it sub_type
            - If sub_type == "object" or "array", need to refer new_metadata_name to retrieve the following Property
            - else, value is optional
    """
    if data_schema.type == "object":
        specific_properties = get_specific_properties_spec_by_metadata(
            properties_spec_list, data_schema.new_metadata_name
        )
        properties_schema.properties = {}
        properties_schema.properties[specific_properties.properties_name] = (
            create_properties_schema(specific_properties, properties_spec_list)
        )

    if data_schema.type == "array":
        if data_schema.sub_type in ("object", "array"):
            specific_properties = get_specific_properties_spec_by_metadata(
                properties_spec_list, data_schema.new_metadata_name
            )
            properties_schema.items = create_properties_schema(
                specific_properties, properties_spec_list
            )
        else:
            properties_schema.items = PropertiesSchema(
                type=data_schema.sub_type if data_schema.sub_type != "" else "string",
                enum=data_schema.value,
            )


def create_properties_schema_by_type(value: Any) -> PropertiesSchema:  # noqa: ANN401
    value_type = type(value).__name__ if value else "str"
    if value_type == "list":
        items = create_properties_schema_by_type(value[0])
        return PropertiesSchema(
            type=type_mapping.get(value_type, "string"), items=items
        )

    return PropertiesSchema(type=type_mapping.get(value_type, "string"))


def create_param_list(
    params: Union[list[PropertiesSpec], list[UrlParams], list[QueryParams]],
) -> dict[str, Union[list[PropertiesSpec], list[UrlParams], list[QueryParams]]]:
    return (
        {
            param.metadata_name
            if isinstance(param, PropertiesSpec)
            else param.name: param
            for param in params
        }
        if params is not None
        else {}
    )


def convert_base_header_to_opanapi_spec_format(
    component_parameters: dict, base_headers: list[BaseHeaderConfig]
) -> None:
    """
    Convert base headers to OpenAPI specification format.
    """
    # Iterate over base_headers
    for base_header in base_headers:
        # Convert base_header to a ParameterSchema
        base_header_schema = create_parameter_schema(
            base_header, PARAMETERS_SCHEMA_IN_HEADER
        )

        # Add the ParameterSchema to the dictionary
        component_parameters[base_header_schema.name] = base_header_schema

    return component_parameters


def convert_path_specification_to_opanapi_spec_format(
    path_parameters: dict, path_specifications: list[PathConfig]
) -> None:
    """
    Convert path config to OpenAPI specification format.
    """
    # Iterate over path_specification
    for path_specification in path_specifications:
        # Convert path_specification to a Parameters
        all_parameters = create_path_parameter_schema(
            path_specification.custom_headers
            if path_specification.custom_headers is not None
            else [],
            path_specification.url_params
            if path_specification.url_params is not None
            else [],
            path_specification.query_params
            if path_specification.query_params is not None
            else [],
            path_specification.path,
        )

        # Create an instance of PropertiesSchema for request body
        request_properties = convert_request_body_properties_to_opanapi_spec_format(
            path_specification.request_body_schema
        )

        request_scheme = RequestScheme(
            content=ContentSchema(
                application_json=ApplicationJsonSchema(
                    schema_=RequestResponseDetails(
                        properties=request_properties["properties"],
                        required=request_properties["required"],
                    )
                )
            )
        )

        # Create an instance of PropertiesSchema for response body
        response_scheme = {}
        for response_body in path_specification.response_body_schema:
            response_properties = (
                convert_request_body_properties_to_opanapi_spec_format(response_body)
            )
            response_scheme[response_body.status_code] = ResponseScheme(
                description=response_body.response_description,
                content=ContentSchema(
                    application_json=ApplicationJsonSchema(
                        schema=RequestResponseDetails(
                            properties=response_properties["properties"],
                            required=response_properties["required"],
                        )
                    )
                ),
            )

        path_details_schema = PathDetailsSchema(
            summary=path_specification.summary,
            parameters=all_parameters,
            requestBody=request_scheme
            if path_specification.method.lower() != "get"
            else None,
            responses=response_scheme,
        )

        # Remove query params
        # Convert the path to the OpenAPI format
        parsed_url = urlparse(path_specification.path)
        openapi_path = parsed_url.path.replace("{{", "{").replace("}}", "}")

        # Add the ParameterSchema to the dictionary
        path_parameters[openapi_path] = {path_specification.method: path_details_schema}


def convert_request_body_properties_to_opanapi_spec_format(
    request_response_body: RequestBodySchema | ResponseBodySchema,
) -> dict:
    """
    Convert request/ response body to OpenAPI specification format.
    """
    body_details = request_response_body.body_details

    # Convert the body details JSON string to a Python dictionary
    body_details_json = json.loads(body_details)

    # Convert the properties spec list to a dictionary
    properties_spec_list = create_param_list(request_response_body.properties_spec)
    properties = {}
    required: list[str] = []

    # Iterate over the keys and values in the dictionary
    for key, value in body_details_json.items():
        if re.match(r"{{.*}}", key):
            real_key = key.replace("{", "").replace("}", "")

            specific_properties = get_specific_properties_spec_by_metadata(
                properties_spec_list, real_key
            )
            properties_spec_list[real_key]

            if specific_properties.type is None:
                input_type = type(value).__name__ if value else "str"
                specific_properties.type = type_mapping.get(input_type, "string")

            check_properties_required(required, specific_properties)

            properties_schema = create_properties_schema(
                specific_properties, properties_spec_list
            )
            if properties_schema.type == "array" and properties_schema.items is None:
                properties_schema.items = create_properties_schema_by_type(value)

            properties[specific_properties.properties_name] = properties_schema
            continue

        properties[key] = create_properties_schema_by_type(value)

    return {"properties": properties, "required": required}


def get_specific_properties_spec_by_metadata(
    properties_spec_list: dict[Any, PropertiesSpec],
    new_metadata_name: str,
) -> PropertiesSpec:
    """
    Retrieve a specific PropertiesSpec instance by metadata name from a list of property specifications.

    This function takes a dictionary of property specifications and a metadata name,
    and returns a PropertiesSpec instance that matches the given metadata name.
    """
    properties_spec = properties_spec_list.get(new_metadata_name)
    if not properties_spec:
        err_message = f"No Property found for metadata name {new_metadata_name}"
        raise ValueError(err_message)
    return properties_spec


def is_secret_key(key: str) -> tuple[bool]:
    # Search for a pattern like '{{SECRET:<key-name>}}' in the value
    match = re.search(r"\{\{(.*?):(.*?)\}\}", key)
    if match:
        # Extract the value between '{{' and '}}'
        secret_type = match.group(1)
        # Check if the secret_value is 'secret'
        if secret_type.upper() == "SECRET":
            return True
    return False


def check_secret_prefix_and_get_secret_name(key: str) -> tuple[bool, str]:
    # Search for a pattern like '{...}' in the value
    match = re.search(r"\{\{(.*?):(.*?)\}\}", key)
    if match:
        # Extract the value between '{{' and '}}'
        secret_type = match.group(1)
        key = match.group(2)
        # Check if the secret_value is 'secret'
        if secret_type.upper() != "SECRET":
            return False, key
    return True, key


def check_properties_required(required: list[str], properties: PropertiesSpec) -> None:
    if properties.value and properties.required:
        required.append(properties.properties_name)


def extract_url_param(path: str) -> list[str]:
    # Find all URL parameters in the URL
    return re.findall(parameter_pattern, path)


def extract_query_param(query: str) -> dict[str, list[str]]:
    # Parse the query string into a dictionary
    return parse_qs(query)


# Define a dictionary that maps Python data types to OpenAPI data types
type_mapping = {
    "": "string",
    "str": "string",
    "int": "integer",
    "bool": "boolean",
    "list": "array",
    "dict": "object",
}

# Regular expression to match URL parameters
parameter_pattern = r"\{\{(.*?)\}\}"
