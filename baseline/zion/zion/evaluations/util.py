from __future__ import annotations

import json
from typing import Any

from langsmith import schemas

from zion.agent.zion_agent_classes import (
    ZionAgentInput,
)
from zion.config import global_config
from zion.evaluations.level_zero_test_cases import (
    slack_channel_specific_instruction,
)


def convert_str_to_json(input_data: dict[str, Any], key: str, value: Any) -> None:  # noqa: ANN401
    if isinstance(value, str):
        try:
            input_data[key] = json.loads(value)
        except json.JSONDecodeError:
            input_data[key] = {}


def check_plugin(
    plugins: list[dict[str, Any]] | None, input_data: dict[str, Any]
) -> None:
    if plugins is None:
        input_data["agent_config"]["plugins"] = [
            {
                "name": "glean_search",
                "type": "common",
                "metadata": {
                    "datasourcesFilter": [
                        "confluence",
                        "gdrive",
                        "techdocs",
                        "alltechdocs",
                        "hubble",
                    ]
                },
            }
        ]
        return

    for plugin in plugins:
        if plugin["name"] == "glean_search" and plugin["metadata"] is None:
            plugin["metadata"] = {
                "datasourcesFilter": [
                    "confluence",
                    "gdrive",
                    "techdocs",
                    "alltechdocs",
                    "hubble",
                ]
            }
            break
    input_data["agent_config"]["plugins"] = plugins

    return


def parse_example_agent_executor(
    example: schemas.Example, agent_input: ZionAgentInput | None
) -> schemas.Example:
    # Access the 'input' dictionary from the Example
    input_data = example.inputs

    input_data = generate_example_data(input_data, agent_input)

    # Check if 'agent_config', 'system_prompt_variables', 'query_source' and 'chat_history' is a string
    agent_config_str = input_data.get("agent_config")
    system_prompt_variables_str = input_data.get("system_prompt_variables")
    if system_prompt_variables_str == {}:
        input_data["system_prompt_variables"]["slack_channel_specific_instruction"] = (
            slack_channel_specific_instruction
        )
    query_source_str = input_data.get("query_source")
    chat_history_str = input_data.get("chat_history")

    # Check and convert the data to json
    convert_str_to_json(input_data, "agent_config", agent_config_str)
    convert_str_to_json(
        input_data, "system_prompt_variables", system_prompt_variables_str
    )
    convert_str_to_json(input_data, "query_source", query_source_str)
    convert_str_to_json(input_data, "chat_history", chat_history_str)

    return example


def generate_example_data(
    input_data: dict[str, Any], agent_input: ZionAgentInput | None
) -> dict[str, Any]:
    if agent_input is not None:
        if agent_input.system_prompt_variables is not None:
            input_data["system_prompt_variables"] = agent_input.system_prompt_variables
        else:
            input_data["system_prompt_variables"] = {}
            input_data["system_prompt_variables"][
                "slack_channel_specific_instruction"
            ] = slack_channel_specific_instruction
        input_data["system_prompt_hub_commit"] = (
            agent_input.system_prompt_hub_commit
            if agent_input.system_prompt_hub_commit is not None
            else global_config.request_system_prompt
        )

        input_data["structured_response_schema_hub_commit"] = (
            global_config.response_system_prompt
        )

        input_data["agent_config"] = agent_input.agent_config.model_dump()
        input_data["chat_history"] = agent_input.chat_history
    else:
        input_data["system_prompt_variables"] = {}
        input_data["system_prompt_variables"]["slack_channel_specific_instruction"] = (
            slack_channel_specific_instruction
        )

        input_data["system_prompt_hub_commit"] = global_config.request_system_prompt

        input_data["structured_response_schema_hub_commit"] = (
            global_config.response_system_prompt
        )

        input_data["chat_history"] = []

    check_plugin(input_data["agent_config"]["plugins"], input_data)

    return input_data


def parse_example_multi_agent(
    example: schemas.Example, agent_input: ZionAgentInput | None
) -> schemas.Example:
    # Access the 'input' dictionary from the Example
    input_data = example.inputs

    input_data = generate_example_data_multi_agent(input_data, agent_input)

    # Check if 'agent_config', 'system_prompt_variables', 'query_source' and 'chat_history' is a string
    agent_config_str = input_data.get("agent_config")
    chat_history_str = input_data.get("chat_history")

    # Check and convert the data to json
    convert_str_to_json(input_data, "agent_config", agent_config_str)
    convert_str_to_json(input_data, "chat_history", chat_history_str)

    return example


def generate_example_data_multi_agent(
    input_data: dict[str, Any], agent_input: ZionAgentInput | None
) -> dict[str, Any]:
    if agent_input is not None:
        input_data["agent_config"] = agent_input.agent_config.model_dump()
        input_data["chat_history"] = agent_input.chat_history
        input_data["system_prompt_variables"] = agent_input.system_prompt_variables
    else:
        input_data["chat_history"] = []

    check_plugin(input_data["agent_config"]["plugins"], input_data)

    return input_data
