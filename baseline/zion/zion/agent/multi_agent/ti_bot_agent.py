# ruff: noqa: T201

from collections.abc import Sequence
from typing import Callable

from langchain_community.tools import BaseTool
from langchain_core.messages import AIMessage
from langgraph.prebuilt import create_react_agent

from zion.agent.model import ChatGrabGPT
from zion.agent.multi_agent.agent_actions import extract_agent_actions_from_messages
from zion.agent.multi_agent.classes import AgentState


def create_ti_bot_agent_node(
    model: ChatGrabGPT, prompt: str, ti_bot_tools: Sequence[BaseTool]
) -> Callable:
    ti_bot_agent = create_react_agent(
        model=model,
        tools=ti_bot_tools,
        prompt=prompt,
    )

    def ti_bot_agent_node(state: AgentState) -> AgentState:
        response = ti_bot_agent.invoke(state)

        response_content = ""
        if response["messages"][-1].content:  # check if content is not None
            response_content = response["messages"][-1].content

        # extract agent actions by iterating over only new messages added by ti_bot_agent
        agent_actions = extract_agent_actions_from_messages(
            response["messages"][len(state["messages"]) : len(response["messages"])]
        )

        return {
            "messages": [AIMessage(content=response_content, name="ti_bot_agent")],
            "agent_actions": agent_actions,
        }

    return ti_bot_agent_node
