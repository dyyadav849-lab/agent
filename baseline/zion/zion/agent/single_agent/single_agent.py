from collections.abc import Sequence
from operator import add
from typing import Annotated, Callable, TypedDict

from langchain_community.tools import BaseTool
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
)
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

from zion.agent.model import ChatGrabGPT
from zion.agent.multi_agent.agent_actions import extract_agent_actions_from_messages
from zion.agent.multi_agent.classes import Source
from zion.agent.multi_agent.constant import SOURCES_DESCRIPTION
from zion.tool.agent_tool import ZionAgentActions


class SingleAgentState(TypedDict):
    """The state of the agent."""

    messages: Annotated[Sequence[BaseMessage], add_messages]
    sources: list[Source]
    agent_actions: Annotated[list[ZionAgentActions], add]


class SingleAgentStructuredRespDescriptions:
    sources_description: str

    def __init__(self, sources_description: str = SOURCES_DESCRIPTION) -> None:
        self.sources_description = sources_description


DEFAULT_SINGLE_AGENT_PROMPT = """
You are a helpful AI assistant.

If your tool calls don't provide enough context, stop and ask the user to clarify their question or provide more context.

Query all relevant tools, never use pre-trained knowledge. Keep your answers to STRICTLY FEWER THAN 50 words.
"""


class SingleAgentPrompts:
    single_agent_prompt: str

    def __init__(
        self, single_agent_prompt: str = DEFAULT_SINGLE_AGENT_PROMPT
    ) -> None:
        self.single_agent_prompt = single_agent_prompt


def create_single_agent_response(
    descriptions: SingleAgentStructuredRespDescriptions,
) -> BaseModel:
    class SingleAgentResponse(BaseModel):
        sources: list[Source] = Field(description=descriptions.sources_description)

    return SingleAgentResponse


def create_single_agent_node(
    model: ChatGrabGPT,
    prompt: str,
    single_agent_tools: Sequence[BaseTool],
    descriptions: SingleAgentStructuredRespDescriptions,
) -> Callable:
    single_agent = create_react_agent(
        model=model,
        tools=single_agent_tools,
        response_format=create_single_agent_response(descriptions),
        prompt=prompt,
    )

    def single_agent_node(
        state: SingleAgentState,
    ) -> SingleAgentState:
        response = single_agent.invoke(state)

        response_content = ""
        if response["messages"][-1].content:  # check if content is not None
            response_content = response["messages"][-1].content

        # extract agent actions by iterating over only new messages added by last iteration of agent
        agent_actions = extract_agent_actions_from_messages(
            response["messages"][len(state["messages"]) : len(response["messages"])]
        )

        return {
            "messages": [
                AIMessage(content=response_content, name="single_agent")
            ],
            "agent_actions": agent_actions,
        }

    return single_agent_node
