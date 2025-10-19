from zion.data.agent_plugin.data import AgentPlugin
from zion.data.agent_plugin.util import get_agent_plugin_json, get_agent_plugin_map


def test_get_agent_plugin_json() -> None:
    """Test if we can convert agent plugin collection to a json format."""
    db_agent_return_val = [
        AgentPlugin(
            name_for_model="plugin1",
            schema_version="1.0",
            type="common",
            name_for_human="plugin 1",
            description_for_model="plugin 1 description model",
            description_for_human="plugin 1 description human",
            api={},
            owner=[],
            http_plugin_detail=None,
            is_moved=False,
            orchestrators_plugin=None,
        ),
        AgentPlugin(
            name_for_model="plugin2",
            schema_version="2.0",
            type="openapi",
            name_for_human="plugin 2",
            description_for_model="plugin 2 description model",
            description_for_human="plugin 2 description human",
            api={},
            owner=[],
            http_plugin_detail=None,
            is_moved=False,
            orchestrators_plugin=None,
        ),
    ]

    agent_data_json = get_agent_plugin_json(db_agent_return_val, open_api=False)

    expected_agent_data_json = [
        {
            "schema_version": "1.0",
            "name_for_model": "plugin1",
            "name_for_human": "plugin 1",
            "description_for_model": "plugin 1 description model",
            "description_for_human": "plugin 1 description human",
            "type": "common",
            "owner": [],
            "api": {},
            "http_plugin_detail": None,
            "orchestrators_plugin": None,
        },
        {
            "schema_version": "2.0",
            "name_for_model": "plugin2",
            "name_for_human": "plugin 2",
            "description_for_model": "plugin 2 description model",
            "description_for_human": "plugin 2 description human",
            "type": "openapi",
            "owner": [],
            "api": {},
            "http_plugin_detail": None,
            "orchestrators_plugin": None,
        },
    ]
    assert agent_data_json == expected_agent_data_json


def test_get_agent_plugin_map() -> None:
    """Test if we can convert agent plugin collection to a map, where the name_for_model is the key."""
    common_plugin1 = AgentPlugin(
        name_for_model="plugin1", schema_version="1.0", type="common"
    )
    openapi_plugin1 = AgentPlugin(
        name_for_model="plugin2", schema_version="2.0", type="openapi"
    )
    openapi_plugin2 = AgentPlugin(
        name_for_model="plugin3", schema_version="3.0", type="openapi"
    )
    http_plugin1 = AgentPlugin(
        name_for_model="plugin4", schema_version="3.0", type="http"
    )
    ochestrator_plugin1 = AgentPlugin(
        name_for_model="plugin5", schema_version="3.0", type="orchestrator"
    )
    agent_plugins = [
        common_plugin1,
        openapi_plugin1,
        openapi_plugin2,
        http_plugin1,
        ochestrator_plugin1,
    ]
    expected_result = {
        "common": {
            "plugin1": common_plugin1,
        },
        "openapi": {"plugin2": openapi_plugin1, "plugin3": openapi_plugin2},
        "http": {"plugin4": http_plugin1},
        "orchestrator": {"plugin5": ochestrator_plugin1},
    }
    assert get_agent_plugin_map(agent_plugins) == expected_result
