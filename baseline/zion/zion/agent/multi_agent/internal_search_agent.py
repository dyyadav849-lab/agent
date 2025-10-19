from collections.abc import Sequence
from typing import Callable

from langchain_community.tools import BaseTool
from langchain_core.messages import AIMessage
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

from zion.agent.model import ChatGrabGPT
from zion.agent.multi_agent.agent_actions import extract_agent_actions_from_messages
from zion.agent.multi_agent.classes import (
    AgentState,
    MultiAgentStructuredRespDescriptions,
    Source,
)


def create_internal_search_response(
    descriptions: MultiAgentStructuredRespDescriptions,
) -> BaseModel:
    class InternalSearchResponse(BaseModel):
        sources: list[Source] = Field(description=descriptions["sources_description"])

    return InternalSearchResponse


# TODO @yisheng.tay: consider adding tool to describe when to call this agent - would help with getting ti_bot_agent to call internal_search_agent when appropriate
def create_internal_search_agent_node(
    model: ChatGrabGPT,
    prompt: str,
    internal_search_tools: Sequence[BaseTool],
    descriptions: MultiAgentStructuredRespDescriptions,
) -> Callable:
    internal_search_agent = create_react_agent(
        model=model,
        tools=internal_search_tools,
        response_format=create_internal_search_response(descriptions),
        prompt=prompt,
    )

    def internal_search_agent_node(state: AgentState) -> AgentState:
        response = internal_search_agent.invoke(state)

        response_content = ""

        if response["messages"][-1].content:  # check if content is not None
            response_content = response["messages"][-1].content

        # extract agent actions by iterating over only new messages added by internal_search_agent
        agent_actions = extract_agent_actions_from_messages(
            response["messages"][len(state["messages"]) : len(response["messages"])]
        )

        return {
            "messages": [
                AIMessage(
                    content=response_content,
                    name="internal_search_agent",
                )
            ],
            "agent_actions": agent_actions,
            "sources": response["structured_response"].sources,
        }

    return internal_search_agent_node
