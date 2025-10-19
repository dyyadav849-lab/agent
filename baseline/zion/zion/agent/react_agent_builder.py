# ruff: noqa: T201
import asyncio
import json
from collections.abc import Sequence
from typing import Annotated, Callable, Optional, TypedDict, Union

from langchain_community.tools import BaseTool
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.prompt_values import ChatPromptValue
from langchain_core.runnables import RunnableConfig
from langgraph.graph.message import add_messages

from zion.agent.model import ChatGrabGPT
from zion.agent.zion_agent_classes import (
    ZionAgentInput,
)
from zion.util.optimize_token import OptimizeToken


class AgentState(TypedDict):
    """The state of the agent."""

    messages: Annotated[Sequence[BaseMessage], add_messages]


# Type alias for tool arguments
ToolArgs = Union[dict, str, int, float, bool, None]
ToolResult = Union[str, dict, list, int, float, bool, None]


def _execute_tool_coroutine(tool: BaseTool, tool_args: ToolArgs) -> ToolResult:
    """Execute tool using coroutine method."""
    if isinstance(tool_args, dict):
        return asyncio.run(tool.coroutine(**tool_args))
    return asyncio.run(tool.coroutine(tool_args))


def _execute_tool_func(tool: BaseTool, tool_args: ToolArgs) -> ToolResult:
    """Execute tool using func method."""
    if isinstance(tool_args, dict):
        if asyncio.iscoroutinefunction(tool.func):
            return asyncio.run(tool.func(**tool_args))
        return tool.func(**tool_args)

    if asyncio.iscoroutinefunction(tool.func):
        return asyncio.run(tool.func(tool_args))
    return tool.func(tool_args)


def _ensure_serializable(tool_result: ToolResult) -> ToolResult:
    """Ensure tool result is JSON serializable."""
    if hasattr(tool_result, "__dict__") and not isinstance(
        tool_result, (str, int, float, bool, list, dict)
    ):
        return str(tool_result)
    if not isinstance(tool_result, (str, int, float, bool, list, dict, type(None))):
        return str(tool_result)
    return tool_result


def _execute_single_tool(tool: BaseTool, tool_args: ToolArgs) -> ToolResult:
    """Execute a single tool and return the result."""
    try:
        # Use the underlying coroutine/function directly to avoid callback manager injection
        if hasattr(tool, "coroutine") and tool.coroutine:
            return _execute_tool_coroutine(tool, tool_args)
        if hasattr(tool, "func") and tool.func:
            return _execute_tool_func(tool, tool_args)
        # Fallback to regular invoke
        return tool.invoke(tool_args)
    except (ValueError, TypeError, AttributeError) as e:
        return f"Tool execution failed: {e!s}"


def _create_tool_message(tool_call: dict, tool_result: ToolResult) -> ToolMessage:
    """Create a ToolMessage from tool call and result."""
    content = (
        json.dumps(tool_result)
        if isinstance(tool_result, (dict, list))
        else str(tool_result)
    )
    return ToolMessage(
        content=content,
        name=tool_call["name"],
        tool_call_id=tool_call["id"],
    )


# Define our tool node
def get_tool_node(tools: Sequence[BaseTool]) -> Callable:
    tools_by_name = {tool.name: tool for tool in tools}

    def tool_node(
        state: AgentState, tools_by_name: Optional[list] = tools_by_name
    ) -> dict:
        outputs = []
        for tool_call in state["messages"][-1].tool_calls:
            if tool_call["name"] not in tools_by_name:
                continue
            tool = tools_by_name[tool_call["name"]]
            tool_args = tool_call["args"]

            # Execute tool and ensure result is serializable
            tool_result = _execute_single_tool(tool, tool_args)
            tool_result = _ensure_serializable(tool_result)

            # Create and add tool message
            outputs.append(_create_tool_message(tool_call, tool_result))

        return {"messages": outputs}

    return tool_node


def get_call_model(model: ChatGrabGPT, system_prompt_str: str) -> Callable:
    # Define the node that calls the model
    def call_model(
        state: AgentState,
        config: RunnableConfig,
        model: Optional[ChatGrabGPT] = model,
    ) -> dict:
        # this is similar to customizing the create_react_agent with state_modifier, but is a lot more flexible
        system_prompt = SystemMessage(system_prompt_str)
        response = model.invoke([system_prompt] + state["messages"], config)
        # We return a list, because this will get added to the existing list
        return {"messages": [response]}

    return call_model


# Define the conditional edge that determines whether to continue or not
def should_continue(state: AgentState) -> str:
    messages = state["messages"]
    last_message = messages[-1]
    # If there is no function call, then we finish
    if not last_message.tool_calls:
        return "end"
    # Otherwise if there is, we continue
    return "continue"


def get_optimize_token(model: ChatGrabGPT) -> Callable:
    def optimize_token(state: AgentState, model: Optional[ChatGrabGPT] = model) -> None:
        optimized_messages = OptimizeToken(model).optimize_token(
            ChatPromptValue(messages=state["messages"])
        )
        state["messages"] = optimized_messages.messages

    return optimize_token


def convert_input_to_react_agent_message_dict(agent_input: ZionAgentInput) -> dict:
    chat_mesages = [HumanMessage(content=agent_input.input)]
    if agent_input.chat_history is not None:
        chat_mesages = agent_input.chat_history + chat_mesages
    return {"messages": chat_mesages}
