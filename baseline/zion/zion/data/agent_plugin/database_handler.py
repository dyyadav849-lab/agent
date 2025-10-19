from typing import Optional

from sqlalchemy.sql import and_, select, update

from zion.config import logger
from zion.data.agent_plugin.constant import (
    AGENT_OPENAPI_PLUGIN_TYPE,
)
from zion.data.agent_plugin.data import AgentPlugin, QueryAgentPluginRequest
from zion.data.agent_plugin.filter_condition import construct_plugin_query_conditions
from zion.data.agent_plugin.util import (
    get_http_plugin_detail_dict,
    get_plugin_api_info_dict,
)
from zion.data.connection import get_session
from zion.openapi.openapi_plugin import OpenAPIPlugin


def get_agent_plugin_database(
    query_agent_plugin_req: QueryAgentPluginRequest,
) -> list[AgentPlugin] | None:
    """Gets the agent plugin from database based on the agent_name, username and channel_name"""
    query_conditions = construct_plugin_query_conditions(query_agent_plugin_req)

    with get_session() as db:
        agent_plugins = db.execute(
            select(AgentPlugin).filter(
                and_(
                    AgentPlugin.is_moved.is_(False),
                    *query_conditions,
                )
            )
        ).all()

        if agent_plugins is None:
            message = f"Agent Plugin with channel_name {query_agent_plugin_req.channel_name}, agent_name {query_agent_plugin_req.agent_name}, username {query_agent_plugin_req.username} not found"
            logger.info(message)
            return []

        # we extract the agent plugin data from the query data returned from DB
        return [agent_plugin_data for (agent_plugin_data,) in agent_plugins]


def get_all_agent_plugins_database(
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    name_for_human: Optional[str] = None,
) -> list[AgentPlugin] | None:
    """Gets all the agent plugins from the database"""
    try:
        with get_session() as db:
            query = select(AgentPlugin).filter(AgentPlugin.is_moved.is_(False))

            if name_for_human:
                query = query.where(
                    AgentPlugin.name_for_human.like(f"%{name_for_human}%")
                )

            query = query.order_by(AgentPlugin.type)

            # If page and page_size are provided, calculate offset and limit
            if page is not None and page_size is not None:
                offset = (page - 1) * page_size
                query = query.offset(offset).limit(page_size)

            agent_plugins = db.execute(query).all()

            if agent_plugins is None:
                logger.info("No Agent Plugins found")
                return []

            # we extract the agent plugin data from the query data returned from DB
            return [agent_plugin_data for (agent_plugin_data,) in agent_plugins]
    except Exception as e:  # noqa:BLE001 message:do not blind catch
        log_message = f"Error: {e!s}"
        logger.exception(log_message)
        return []


def get_specific_agent_plugins_database(
    name_for_model: str, page: Optional[int] = None, page_size: Optional[int] = None
) -> list[AgentPlugin] | None:
    """Gets all the agent plugins from the database"""
    with get_session() as db:
        query = select(AgentPlugin).filter(
            and_(
                AgentPlugin.is_moved.is_(False),
                AgentPlugin.name_for_model == name_for_model,
            )
        )

        # If page and page_size are provided, calculate offset and limit
        if page is not None and page_size is not None:
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size)

        agent_plugins = db.execute(query).all()

        if agent_plugins is None:
            logger.info("No Agent Plugins found")
            return []

        # we extract the agent plugin data from the query data returned from DB
        return [agent_plugin_data for (agent_plugin_data,) in agent_plugins]


def set_all_plugin_to_is_moved() -> None:
    """Sets all openapi plugin to is moved.
    This function is called at the start of sync agent plugin
    This will ensure that plugins that are moved/deleted will not show up in our database.
    Setting it to moved is ONLY applicable for openapi plugins.

    """

    # query for all openapi plugin that is moved is false
    with get_session() as db:
        db.execute(
            update(AgentPlugin)
            .where(
                and_(
                    AgentPlugin.is_moved.is_(False),
                    AgentPlugin.type == AGENT_OPENAPI_PLUGIN_TYPE,
                )
            )
            .values(is_moved=True)
        )
        db.commit()


def save_agent_plugin_to_db(agent_plugin_yaml: dict[str, any]) -> None:
    """Saves agent plugin to database.
    If the agent plugin is already available in the database, we can update it instead of saving a new entry

    """

    # check if the agent plugin is already in database,
    # if yes update it else save a new entry into database

    # check if name for model is invalid, if yes return
    name_for_model = agent_plugin_yaml.get("name_for_model", "")
    if name_for_model == "":
        return

    with get_session() as db:
        agent_plugin = db.execute(
            select(AgentPlugin).where(AgentPlugin.name_for_model == name_for_model)
        ).all()

        if agent_plugin is None or len(agent_plugin) == 0:
            # save new agent plugin to database
            new_agent_plugin = AgentPlugin(
                schema_version=agent_plugin_yaml.get(
                    AgentPlugin.schema_version.name, ""
                ),
                name_for_model=agent_plugin_yaml.get(
                    AgentPlugin.name_for_model.name, ""
                ),
                name_for_human=agent_plugin_yaml.get(
                    AgentPlugin.name_for_human.name, ""
                ),
                description_for_model=agent_plugin_yaml.get(
                    AgentPlugin.description_for_model.name, ""
                ),
                description_for_human=agent_plugin_yaml.get(
                    AgentPlugin.description_for_human.name, ""
                ),
                type=agent_plugin_yaml.get(AgentPlugin.type.name, ""),
                api=agent_plugin_yaml.get(AgentPlugin.api.name, {}),
                is_moved=False,
            )
            db.add(new_agent_plugin)
            db.commit()
            db.refresh(new_agent_plugin)

            return

        # update the agent plugin in database
        db.execute(
            update(AgentPlugin)
            .where(AgentPlugin.name_for_model == name_for_model)
            .values(
                name_for_human=agent_plugin_yaml.get("name_for_human", ""),
                description_for_model=agent_plugin_yaml.get(
                    "description_for_model", ""
                ),
                description_for_human=agent_plugin_yaml.get(
                    "description_for_human", ""
                ),
                type=agent_plugin_yaml.get("type", ""),
                api=agent_plugin_yaml.get("api", {}),
                is_moved=False,
            )
        )
        db.commit()


def duplicate_agent_plugin_checking(name_for_model: str) -> None:
    # query for checkign duplicate plugin agent
    with get_session() as db:
        agent_plugin = db.execute(
            select(AgentPlugin).where(AgentPlugin.name_for_model == name_for_model)
        ).all()

        message = f"Duplicate plugin ({name_for_model}) detected"

        if agent_plugin:
            raise ValueError(message)


def create_agent_plugin(plugin_info: OpenAPIPlugin) -> None:
    # query for creating new agent plugin
    with get_session() as db:
        plugin_api_info = get_plugin_api_info_dict(plugin_info)
        http_plugin_detail = (
            get_http_plugin_detail_dict(plugin_info)
            if plugin_info.http_plugin_detail is not None
            else {}
        )

        orchestrator_plugin_detail = plugin_info.orchestrators_plugin.dict(
            by_alias=True
        )

        new_plugin = AgentPlugin(
            name_for_model=plugin_info.name_for_model,
            name_for_human=plugin_info.name_for_human,
            schema_version=plugin_info.schema_version,
            description_for_model=plugin_info.description_for_model,
            description_for_human=plugin_info.description_for_human,
            type=plugin_info.type,
            owner=plugin_info.owner,
            api=plugin_api_info,
            http_plugin_detail=http_plugin_detail,
            orchestrators_plugin=orchestrator_plugin_detail,
        )
        db.add(new_plugin)
        db.commit()


def update_agent_plugin(plugin_info: OpenAPIPlugin) -> None:
    # query for updating agent plugin
    with get_session() as db:
        plugin_api_info = get_plugin_api_info_dict(plugin_info)
        http_plugin_detail = (
            get_http_plugin_detail_dict(plugin_info)
            if plugin_info.http_plugin_detail is not None
            else {}
        )

        orchestrator_plugin_detail = plugin_info.orchestrators_plugin.dict(
            by_alias=True
        )

        db.execute(
            update(AgentPlugin)
            .where(AgentPlugin.name_for_model == plugin_info.name_for_model)
            .values(
                schema_version=plugin_info.schema_version,
                name_for_human=plugin_info.name_for_human,
                description_for_model=plugin_info.description_for_model,
                description_for_human=plugin_info.description_for_human,
                type=plugin_info.type,
                owner=plugin_info.owner,
                api=plugin_api_info,
                http_plugin_detail=http_plugin_detail,
                orchestrators_plugin=orchestrator_plugin_detail,
            )
        )

        db.commit()


def set_plugin_to_is_moved(plugin_info: OpenAPIPlugin) -> None:
    """Sets plugin to is moved by name_for_model."""

    # query for plugin that is moved is false and name_for_model is same with plugin_info.name_for_model
    with get_session() as db:
        db.execute(
            update(AgentPlugin)
            .where(
                and_(
                    AgentPlugin.is_moved.is_(False),
                    AgentPlugin.name_for_model == plugin_info.name_for_model,
                )
            )
            .values(is_moved=True)
        )
        db.commit()
