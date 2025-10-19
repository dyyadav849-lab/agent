from zion.data.agent_plugin.constant import (
    AGENT_COMMON_PLUGIN_TYPE,
    AGENT_HTTP_PLUGIN_TYPE,
    AGENT_OCHESTRATOR_PLUGIN_TYPE,
    AGENT_OPENAPI_PLUGIN_TYPE,
)
from zion.data.agent_plugin.data import AgentPlugin
from zion.data.agent_plugin.http_plugin import (
    create_base_headers,
    create_request_body_schema,
    create_response_body_schema,
    decrypt_base_headers_secret_value,
)
from zion.openapi.openapi_plugin import (
    AccessControlConfig,
    AgentsConfig,
    ApiConfig,
    HttpPluginConfig,
    IncludeOpenAPIPath,
    OpenAPIPlugin,
    PathConfig,
    ServerEnvMetadata,
    ServerMetadata,
)


def get_agent_plugin_map(
    agent_plugins: list[AgentPlugin],
) -> dict[str, dict[str, AgentPlugin]]:
    """Convert the list of agent plugin to a hashmap
    The name_for_model will be the key, since this should be a unique value
    """
    agent_plugin_map = {}
    # the agent_plugin_map will be like so
    """
    {
        "common": {
            "universal_search" :agent_plugin_data,
        },
        "openapi":{
            "ti-support-bot": agent_plugin_data,
        },
        "http":{
            "hades": agent_plugin_data,
        }
    }
    """

    common_agent_plugin_collection = {}
    openapi_agent_pligin_collection = {}
    http_agent_plugin_collection = {}
    orchestrator_plugin_collection = {}
    for agent_plugin in agent_plugins:
        name_for_model = agent_plugin.name_for_model
        if agent_plugin.type == AGENT_COMMON_PLUGIN_TYPE:
            common_agent_plugin_collection[name_for_model] = agent_plugin
        elif agent_plugin.type == AGENT_OPENAPI_PLUGIN_TYPE:
            openapi_agent_pligin_collection[name_for_model] = agent_plugin
        elif agent_plugin.type == AGENT_HTTP_PLUGIN_TYPE:
            http_agent_plugin_collection[name_for_model] = agent_plugin
        elif agent_plugin.type == AGENT_OCHESTRATOR_PLUGIN_TYPE:
            orchestrator_plugin_collection[name_for_model] = agent_plugin

    # setting common plugin to the map
    agent_plugin_map[AGENT_COMMON_PLUGIN_TYPE] = common_agent_plugin_collection

    # setting openapi plugin to the map
    agent_plugin_map[AGENT_OPENAPI_PLUGIN_TYPE] = openapi_agent_pligin_collection

    # setting http plugin to the map
    agent_plugin_map[AGENT_HTTP_PLUGIN_TYPE] = http_agent_plugin_collection

    # setting orchestrator plugin to the map
    agent_plugin_map[AGENT_OCHESTRATOR_PLUGIN_TYPE] = orchestrator_plugin_collection

    return agent_plugin_map


def get_agent_plugin_json(
    db_agent_plugins: list[AgentPlugin],
    open_api: bool,  # noqa: FBT001
) -> list[dict[str, any]]:
    """Get a list of agent plugin based on agent_name, username and channel_name. Calls helper function get_agent_plugin_database to get plugins from the database

    Returns data in a map format. Only returns 'name_for_model', 'name_for_human', 'description_for_model', 'description_for_human', 'type' and 'api' fields

    """
    agent_plugin_list = []

    for db_agent_plugin in db_agent_plugins:
        if db_agent_plugin.http_plugin_detail:
            http_plugin_detail = HttpPluginConfig(**db_agent_plugin.http_plugin_detail)

            if not open_api:
                # Decrypted base_header
                decrypt_base_headers_secret_value(http_plugin_detail.base_headers)

                # Decrypted custom_headers
                for path_spec in http_plugin_detail.path_specification:
                    decrypt_base_headers_secret_value(path_spec.custom_headers)

        agent_plugin_list.append(
            {
                "schema_version": db_agent_plugin.schema_version,
                "name_for_model": db_agent_plugin.name_for_model,
                "name_for_human": db_agent_plugin.name_for_human,
                "description_for_model": db_agent_plugin.description_for_model,
                "description_for_human": db_agent_plugin.description_for_human,
                "type": db_agent_plugin.type,
                "owner": db_agent_plugin.owner,
                "api": db_agent_plugin.api,
                "http_plugin_detail": http_plugin_detail.dict(by_alias=True)
                if db_agent_plugin.http_plugin_detail
                else None,
                "orchestrators_plugin": db_agent_plugin.orchestrators_plugin,
            }
        )

    return agent_plugin_list


def get_plugin_api_info_dict(plugin_info: OpenAPIPlugin) -> dict:
    """Calls helper function get_plugin_api_info_dict to get plugin api info

    Returns data in a dict format. Only returns 'ref', 'server', 'include_paths' and 'access_control' fields

    """
    agents = AgentsConfig(
        **{
            "ti-bot-dm": plugin_info.api.access_control.agents.ti_bot_dm,
            "ti-bot-level-zero": plugin_info.api.access_control.agents.ti_bot_level_zero,
            "grabgpt-agent": plugin_info.api.access_control.agents.grabgpt_agent,
        }
    )
    server_info = ServerMetadata(
        staging=ServerEnvMetadata(host=plugin_info.api.server.staging.host),
        production=ServerEnvMetadata(host=plugin_info.api.server.production.host),
    )

    include_paths = [
        IncludeOpenAPIPath(path=item.path, method=item.method)
        for item in plugin_info.api.include_paths
    ]

    # Create an AccessControl object
    access_control = AccessControlConfig(agents=agents)

    # Create an ApiInfo object
    api_info = ApiConfig(
        ref=plugin_info.api.ref,
        server=server_info,
        include_paths=include_paths,
        access_control=access_control,
    )
    # Convert the OpenAPIPlugin object to a dict
    return api_info.dict(by_alias=True)


def get_http_plugin_detail_dict(plugin_info: OpenAPIPlugin) -> dict:
    """Calls helper function get_plugin_api_info_dict to get http plugin detail

    Returns data in a dict format. Only returns 'ref', 'server', 'include_paths' and 'access_control' fields

    """
    server_info = ServerMetadata(
        staging=ServerEnvMetadata(
            host=plugin_info.http_plugin_detail.server.staging.host
        ),
        production=ServerEnvMetadata(
            host=plugin_info.http_plugin_detail.server.production.host
        ),
    )

    base_headers = create_base_headers(plugin_info.http_plugin_detail.base_headers)

    path_specification = [
        PathConfig(
            path=item.path,
            summary=item.summary,
            method=item.method,
            query_params=item.query_params,
            url_params=item.url_params,
            custom_headers=create_base_headers(item.custom_headers),
            request_body_schema=create_request_body_schema(item.request_body_schema),
            response_body_schema=create_response_body_schema(item.response_body_schema),
        )
        for item in plugin_info.http_plugin_detail.path_specification
    ]

    # Create an ApiInfo object
    http_plugin = HttpPluginConfig(
        service_name=plugin_info.http_plugin_detail.service_name,
        description=plugin_info.http_plugin_detail.description,
        server=server_info,
        base_headers=base_headers,
        path_specification=path_specification,
    )
    # Convert the OpenAPIPlugin object to a dict
    return http_plugin.dict(by_alias=True)
