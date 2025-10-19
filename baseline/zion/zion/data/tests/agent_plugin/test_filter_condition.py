from sqlalchemy import func
from sqlalchemy.sql import literal

from zion.data.agent_plugin.data import AgentPlugin
from zion.data.agent_plugin.filter_condition import (
    construct_plugin_filter_for_val,
    filter_check_if_key_not_present,
)


def test_filter_check_if_key_not_present() -> None:
    filter_name = "test_filter"
    result = filter_check_if_key_not_present(filter_name)
    assert str(result) == str(
        func.json_extract(AgentPlugin.api, f"$.{filter_name}").is_(None)
    )


def test_construct_plugin_filter_for_val() -> None:
    filter_name = "test_filter"
    filter_value = "test_value"
    result = construct_plugin_filter_for_val(filter_name, filter_value)
    expected_result = (
        func.json_contains(
            func.json_extract(AgentPlugin.api, f"$.{filter_name}"),
            literal(f'"{filter_value}"'),
        )
        == 1
    )
    assert str(result) == str(expected_result)
