from __future__ import annotations

from typing import Any

from langchain_core.agents import AgentActionMessageLog
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from zion.config import logger

INFO_MASKED = "info masked"


class ZionAgentActions(BaseModel):
    tool_call_id: str | None = None
    tool: str | None = None
    tool_input: str | dict | None = None
    tool_output: Any | None = None


def get_zion_agent_actions(
    intermediate_steps: list[tuple[AgentActionMessageLog, str]] | None = None,
) -> list[ZionAgentActions]:
    zion_agent_actions = []

    if intermediate_steps is None:
        intermediate_steps = []

    for tup in intermediate_steps:
        agent_input, output = tup
        if isinstance(agent_input, AgentActionMessageLog):
            agent_tool_action = ZionAgentActions(
                tool=agent_input.tool,
                tool_input=agent_input.tool_input,
                tool_output=output,
            )
            zion_agent_actions.append(agent_tool_action)

    return zion_agent_actions


def mask_inputs(inputs: dict) -> dict:
    """This function is used to mask the inputs specifically for LangSmithClient's hide_inputs usage."""

    if inputs is None:
        return {}

    inputs_copy = inputs.copy()

    if "input" in inputs_copy:
        inputs_copy["input"] = mask_any_value(inputs_copy["input"])

    if "system_prompt" in inputs_copy:
        inputs_copy["system_prompt"] = mask_any_value(inputs_copy["system_prompt"])

    if "chat_history" in inputs_copy:
        inputs_copy["chat_history"] = mask_chat_history(inputs_copy["chat_history"])

    if "system_prompt_variables" in inputs_copy:
        inputs_copy["system_prompt_variables"] = mask_any_value(
            inputs_copy["system_prompt_variables"]
        )

    if "structured_response_schema" in inputs_copy:
        inputs_copy["structured_response_schema"] = mask_any_value(
            inputs_copy["structured_response_schema"]
        )

    if "intermediate_steps" in inputs_copy:
        inputs_copy["intermediate_steps"] = mask_any_value(
            inputs_copy["intermediate_steps"]
        )

    return inputs_copy


def mask_chat_history(value: Any) -> list[HumanMessage] | None:  # noqa: ANN401, intentionally mask Any value
    """Mask any value with INFO_MASKED following by its content length."""

    if value is None:
        return None

    try:
        content_length = len(str(value))
    except (TypeError, AttributeError):
        logger.exception("Error getting content length")
        content_length = "Unknown length"

    return [HumanMessage(content=f"{INFO_MASKED} (len: {content_length})")]


def mask_outputs(outputs: dict) -> dict:
    """This function is used to mask the outputs specifically for LangSmithClient's hide_outputs usage."""

    if outputs is None:
        return {}

    if "output" in outputs:
        outputs["output"] = mask_any_value(outputs["output"])

    if "structured_response" in outputs:
        outputs["structured_response"] = mask_any_value(outputs["structured_response"])

    return outputs


def mask_any_value(value: Any) -> str | None:  # noqa: ANN401, intentionally mask Any value
    """Mask any value with INFO_MASKED following by its content length."""

    if value is None:
        return None

    try:
        content_length = len(str(value))
    except (TypeError, AttributeError):
        logger.exception("Error getting content length")
        content_length = "Unknown length"

    return f"{INFO_MASKED} (len: {content_length})"
