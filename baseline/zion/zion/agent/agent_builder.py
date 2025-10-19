# ruff: noqa: T201

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Optional

from langchain.agents import AgentExecutor
from langchain.agents.format_scratchpad.openai_tools import (
    format_to_openai_tool_messages,
)
from langchain.prompts import MessagesPlaceholder
from langchain.schema import AIMessage, FunctionMessage, HumanMessage
from langchain_community.tools import BaseTool
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSerializable
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import BaseModel, Field

from zion.agent.model import ChatGrabGPT
from zion.config import global_config
from zion.util.optimize_token import OptimizeToken

MEMORY_KEY = "chat_history"
SCRATCHPAD_KEY = "agent_scratchpad"


class BaseAgentInput(BaseModel):
    input: str
    chat_history: list[HumanMessage | AIMessage | FunctionMessage] | None = Field(
        default_factory=list
    )


class BaseAgentOutput(BaseModel):
    output: str


def get_agent_chain(
    chat_open_ai: ChatGrabGPT,
    system_prompt: str,
    system_prompt_variables: dict[str, Any],
    tools: Sequence[BaseTool],
    output_parser: classmethod[BaseModel],
) -> RunnableSerializable[Any, list[AgentAction] | AgentFinish]:
    chat_prompt = ChatPromptTemplate.from_messages(
        messages=[
            ("system", system_prompt),
            MessagesPlaceholder(variable_name=MEMORY_KEY),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name=SCRATCHPAD_KEY),
        ]
    )

    llm_with_tools = chat_open_ai.bind()
    if len(tools) > 0:
        llm_with_tools = chat_open_ai.bind(
            tools=[convert_to_openai_tool(tool) for tool in tools]
        )

    input_values = {
        "input": lambda x: x["input"],
        "agent_scratchpad": lambda x: format_to_openai_tool_messages(
            x["intermediate_steps"]
        ),
        "chat_history": lambda x: x["chat_history"],
    }

    # Add additional system prompt variables
    for key, value in system_prompt_variables.items():
        input_values[key] = lambda _, value=value: value

    lcel_flow = input_values | chat_prompt

    if chat_open_ai.model_name.startswith("azure"):
        # optimize token only work for azure model
        lcel_flow = lcel_flow | OptimizeToken(chat_open_ai).optimize_token

    return lcel_flow | llm_with_tools | output_parser()


def get_agent_executor(  # noqa: PLR0913
    chat_open_ai: ChatGrabGPT,
    system_prompt: str,
    system_prompt_variables: dict[str, Any],
    tools: list,
    output_parser: classmethod[BaseModel],
    max_iterations: int,
    input_class: Optional[type[BaseModel]],
    output_class: Optional[type[BaseModel]],
) -> AgentExecutor:
    agent_chain = get_agent_chain(
        chat_open_ai=chat_open_ai,
        tools=tools,
        output_parser=output_parser,
        system_prompt=system_prompt,
        system_prompt_variables=system_prompt_variables,
    )
    agent_executor = AgentExecutor(
        max_iterations=max_iterations,
        handle_parsing_errors=True,  # allows GPT agent to observe error returned caused by GPT
        agent=agent_chain,
        tools=tools,
        verbose=global_config.agent_log_verbose,
        max_execution_time=10 * 60,  # 10 minutes
        return_intermediate_steps=True,
    )

    if input_class and output_class:
        agent_executor = agent_executor.with_types(
            input_type=input_class, output_type=output_class
        )

    return agent_executor
