
from __future__ import annotations

import json

from langchain.agents.output_parsers.openai_tools import (
    OpenAIToolsAgentOutputParser,
    parse_ai_message_to_openai_tool_action,
)
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.outputs import ChatGeneration, Generation

from zion.config import logger

structured_output_delimiter = "<-- structured_response_delimiter -->"


class CustomOpenAIToolsAgentOutputParser(OpenAIToolsAgentOutputParser):
    INVALID_PARSER_ERROR: str = "This output parser only works on ChatGeneration output"

    def parse_result(
        self,
        result: list[Generation],
        *,
        partial: bool = False,  # noqa: ARG002
    ) -> list[AgentAction] | AgentFinish:
        if not isinstance(result[0], ChatGeneration):
            raise TypeError(self.INVALID_PARSER_ERROR)
        message = result[0].message
        action = parse_ai_message_to_openai_tool_action(message)

        # if it's agent finish, reformat the return_values
        if isinstance(action, AgentFinish):
            output, structured_response = parse_structured_response(
                action.return_values["output"]
            )
            action.return_values["output"] = output  # Set the output text
            action.return_values["structured_response"] = structured_response

        return action


def parse_markdown_json_code_block(json_code_block: str) -> dict | None:
    """Parse a JSON code block and return the dict if it exists."""

    json_code_block_stripped = json_code_block.strip()

    structured_output_json = None
    if json_code_block_stripped.startswith(
        "```json"
    ) and json_code_block_stripped.endswith("```"):
        json_in_str = json_code_block_stripped[7:-3]

        try:
            structured_output_json = json.loads(json_in_str)
        except json.decoder.JSONDecodeError:
            logger.error(f"Failed to parse JSON: {json_in_str}")
    return structured_output_json


def parse_structured_response(raw_output: str) -> tuple[str, dict]:
    splitted_output = raw_output.split(f"{structured_output_delimiter}\n")
    output = splitted_output[0]  # Set the output text
    structured_response = {}

    # Set structured_response if it exists
    if len(splitted_output) > 1:
        structured_output_json_block = splitted_output[1]

        result = parse_markdown_json_code_block(structured_output_json_block)
        if result is not None:
            structured_response = result

    return output, structured_response
