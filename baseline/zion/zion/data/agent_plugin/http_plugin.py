from cryptography.fernet import Fernet

from zion.config import global_config
from zion.data.agent_plugin.constant import ENCRYPT_PREFIX
from zion.openapi.http_plugin_to_openapi import is_secret_key
from zion.openapi.openapi_plugin import (
    BaseHeaderConfig,
    PropertiesSpec,
    RequestBodySchema,
    ResponseBodySchema,
)


def create_base_headers(base_headers: list[BaseHeaderConfig]) -> list[BaseHeaderConfig]:
    fernet_key = Fernet(global_config.fernet_key)
    try:
        base_header = []
        for item in base_headers:
            if not is_secret_key(item.name):
                base_header.append(BaseHeaderConfig(name=item.name, value=item.value))
                continue
            value = fernet_key.encrypt(item.value.encode())
            encrypted_value = value.decode()
            base_header.append(
                BaseHeaderConfig(name=item.name, value=ENCRYPT_PREFIX + encrypted_value)
            )

        return base_header  # noqa: TRY300
    except Exception as e:
        raise ValueError(str(e)) from e


def create_properties_spec(
    properties_spec: list[PropertiesSpec],
) -> list[PropertiesSpec]:
    return [
        PropertiesSpec(
            description=item.description,
            required=item.required,
            metadata_name=item.metadata_name,
            properties_name=item.properties_name,
            new_metadata_name=item.new_metadata_name,
            type=item.type,
            sub_type=item.sub_type,
            is_user_specified=item.is_user_specified,
            value=item.value,
            sub_type_details=item.sub_type_details,
        )
        for item in properties_spec
    ]


def create_request_body_schema(
    request_body_schema: RequestBodySchema,
) -> RequestBodySchema:
    return RequestBodySchema(
        body_details=request_body_schema.body_details,
        properties_spec=create_properties_spec(request_body_schema.properties_spec)
        if request_body_schema.properties_spec is not None
        else None,
    )


def create_response_body_schema(
    response_body_schema: list[ResponseBodySchema],
) -> list[ResponseBodySchema]:
    return [
        ResponseBodySchema(
            body_details=item.body_details,
            response_description=item.response_description,
            properties_spec=create_properties_spec(item.properties_spec)
            if item.properties_spec is not None
            else None,
            status_code=item.status_code,
        )
        for item in response_body_schema
    ]


def decrypt_base_headers_secret_value(
    base_headers: list[BaseHeaderConfig],
) -> None:
    fernet_key = Fernet(global_config.fernet_key)

    for item in base_headers:
        value = item.value
        if is_encrypted(value):
            value_without_prefix = value.replace(ENCRYPT_PREFIX, "")
            item.value = fernet_key.decrypt(value_without_prefix.encode()).decode()


def is_encrypted(value: str) -> bool:
    return value.startswith(ENCRYPT_PREFIX)
