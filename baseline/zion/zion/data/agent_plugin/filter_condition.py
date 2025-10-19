from sqlalchemy import BinaryExpression, ColumnElement, func
from sqlalchemy.sql import literal, not_, or_

from zion.data.agent_plugin.constant import (
    AGENT_WHITELIST_ALL,
    QUERY_ACCESS_CONTROL_JSON_STRUCT,
    QUERY_ACCESS_CONTROL_SLACK_CHANNEL_NAME,
    QUERY_ACCESS_CONTROL_USERNAME,
)
from zion.data.agent_plugin.data import AgentPlugin, QueryAgentPluginRequest


def construct_plugin_filter_for_val(
    filter_name: str, filter_value: str
) -> ColumnElement[bool]:
    """Construct a single mysql alchemy filter for searching for plugin from the database. Checks if the filter_value is present inside an array of filter_name"""
    return (
        func.json_contains(
            func.json_extract(AgentPlugin.api, f"$.{filter_name}"),
            literal(f'"{filter_value}"'),
        )
        == 1
    )


def construct_plugin_filter_for_empty_list(filter_name: str) -> ColumnElement[bool]:
    return func.json_length(func.json_extract(AgentPlugin.api, f"$.{filter_name}")) == 0


def construct_plugin_filter_for_null(filter_name: str) -> ColumnElement[bool]:
    """Construct a single mysql alchemy filter for searching for plugin from the database. Checks if the filter_value is has a null value"""

    return (
        func.json_type(func.json_extract(AgentPlugin.api, f"$.{filter_name}")) == "NULL"
    )


def filter_check_if_key_not_present(filter_name: str) -> BinaryExpression[bool]:
    """Construct a filter to check if the filter_name is not present in the api json"""
    return func.json_extract(AgentPlugin.api, f"$.{filter_name}").is_(None)


def construct_plugin_query_conditions(
    query_agent_plugin_req: QueryAgentPluginRequest,
) -> list[ColumnElement[bool]]:
    """Construct all the query condition when searching for plugin from database.
    Checks if the channel name and username is empty, if not it will add it to filter for plugin from the database
    """
    query_conditions: list[ColumnElement[bool]] = []

    # check to set if the agent is defined for the plugin
    query_conditions.append(
        not_(
            filter_check_if_key_not_present(
                f'{QUERY_ACCESS_CONTROL_JSON_STRUCT}."{query_agent_plugin_req.agent_name}"'
            )
        )
    )

    # filter the plugin by keyword
    # we use case insensitive ilike to compare the plugin keyword with the plugin name for human or plugin name for model
    if query_agent_plugin_req.plugin_keyword != "":
        query_conditions.append(
            or_(
                AgentPlugin.name_for_human.ilike(
                    f"%{query_agent_plugin_req.plugin_keyword}%"
                ),
                AgentPlugin.name_for_model.ilike(
                    f"%{query_agent_plugin_req.plugin_keyword}%"
                ),
            )
        )

    plugin_acl_slack_channel_path = f'{QUERY_ACCESS_CONTROL_JSON_STRUCT}."{query_agent_plugin_req.agent_name}".{QUERY_ACCESS_CONTROL_SLACK_CHANNEL_NAME}'
    plugin_acl_username_path = f'{QUERY_ACCESS_CONTROL_JSON_STRUCT}."{query_agent_plugin_req.agent_name}".{QUERY_ACCESS_CONTROL_USERNAME}'

    # add channel specific conditions when querying
    slack_channel_conditions = [
        # we need these conditions, as a plugin can be considered public if:
        # the plugin does not configure slack_channels
        # might be empty list, so need to check if the length is zero.
        filter_check_if_key_not_present(plugin_acl_slack_channel_path),
        construct_plugin_filter_for_val(
            plugin_acl_slack_channel_path,
            AGENT_WHITELIST_ALL,
        ),
        construct_plugin_filter_for_null(
            plugin_acl_slack_channel_path,
        ),
        construct_plugin_filter_for_empty_list(plugin_acl_slack_channel_path),
    ]
    if query_agent_plugin_req.channel_name != "":
        slack_channel_conditions.append(
            construct_plugin_filter_for_val(
                plugin_acl_slack_channel_path,
                query_agent_plugin_req.channel_name,
            )
        )

    query_conditions.append(or_(*slack_channel_conditions))

    # add username specific conditions when querying
    username_conditions = [
        # we need these conditions, as a plugin can be considered public if:
        # the plugin does not configure username
        filter_check_if_key_not_present(plugin_acl_username_path),
        construct_plugin_filter_for_val(
            plugin_acl_username_path,
            AGENT_WHITELIST_ALL,
        ),
        construct_plugin_filter_for_null(
            plugin_acl_username_path,
        ),
    ]

    if query_agent_plugin_req.username != "":
        username_conditions.append(
            construct_plugin_filter_for_val(
                plugin_acl_username_path,
                query_agent_plugin_req.username,
            ),
        )

    query_conditions.append(or_(*username_conditions))

    return query_conditions
