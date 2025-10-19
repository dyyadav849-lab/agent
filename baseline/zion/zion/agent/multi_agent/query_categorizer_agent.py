# ruff: noqa: T201

from enum import Enum
from typing import Callable

from langchain_core.messages import AIMessage
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command
from pydantic import BaseModel, Field

from zion.agent.model import ChatGrabGPT
from zion.agent.multi_agent.classes import (
    AgentState,
    MultiAgentStructuredRespDescriptions,
    ZionCategory,
)


def is_zion_category_answerable(state: AgentState) -> bool:
    return state.get("category") in {ZionCategory.QUERY, ZionCategory.ISSUE}


def is_slack_workflow_category_answerable(state: AgentState) -> bool:
    return state.get("category") in {
        SlackWorkflowCategory.ASK_A_QUESTION,
        SlackWorkflowCategory.REQUEST_A_SERVICE,
        SlackWorkflowCategory.OTHERS,
        SlackWorkflowCategory.DEFAULT_FALLBACK,
        SlackWorkflowCategory.MR_CREATION,
    }


class SlackWorkflowCategory(Enum):
    REPORT_A_BUG = "Report a Bug"
    FEATURE_REQUEST = "Feature Request"
    ASK_A_QUESTION = "Ask a Question"
    REQUEST_A_SERVICE = "Request a Service"
    OTHERS = "Others"
    MR_CREATION = "MR Creation"
    DEFAULT_FALLBACK = "Default"


def create_query_categorizer_response(
    descriptions: MultiAgentStructuredRespDescriptions,
) -> BaseModel:
    class QueryCategorizerResponse(BaseModel):
        category: SlackWorkflowCategory = Field(
            description=descriptions["slack_workflow_category_description"],
        )
        expected_category: SlackWorkflowCategory = Field(
            description=descriptions["expected_slack_workflow_category_description"],
        )

    return QueryCategorizerResponse


def create_query_categorizer_agent_node(
    model: ChatGrabGPT, prompt: str, descriptions: MultiAgentStructuredRespDescriptions
) -> Callable:
    query_categorizer_agent = create_react_agent(
        model=model,
        tools=[],
        response_format=create_query_categorizer_response(descriptions),
        prompt=prompt,
    )

    def query_categorizer_agent_node(state: AgentState) -> Command:
        response = query_categorizer_agent.invoke(state)

        response_content = ""
        if response["messages"][-1].content:  # check if content is not None
            response_content = response["messages"][-1].content
        return Command(
            update={
                "messages": [
                    AIMessage(
                        content=response_content,
                        name="query_categorizer_agent",
                    )
                ],
                "category": response["structured_response"].category,
                "expected_category": response["structured_response"].expected_category,
            },
        )

    return query_categorizer_agent_node
