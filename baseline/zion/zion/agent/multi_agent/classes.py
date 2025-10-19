from collections.abc import Sequence
from enum import Enum
from operator import add
from typing import Annotated

from langchain_core.messages import (
    BaseMessage,
)
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from zion.tool.agent_tool import ZionAgentActions


class Source(TypedDict):
    title: str
    url: str
    source_index: int


class AgentState(TypedDict):
    """The state of the agent."""

    messages: Annotated[Sequence[BaseMessage], add_messages]
    category: str
    expected_category: str
    sources: list[Source]
    able_to_answer: bool
    answer_confidence_scores: Annotated[list[int], add]
    agent_actions: Annotated[list[ZionAgentActions], add]


class MultiAgentStructuredRespDescriptions(TypedDict):
    able_to_answer_description: str
    answer_confidence_score_description: str
    sources_description: str
    slack_workflow_category_description: str
    expected_slack_workflow_category_description: str


class MultiAgentPrompts(TypedDict):
    query_categorizer_agent_prompt: str
    ti_bot_agent_prompt: str
    internal_search_agent_prompt: str
    able_to_answer_agent_prompt: str


class ZionCategory(Enum):
    QUERY = "Query"
    ISSUE = "Issue"
    APPROVAL_VALIDATE = "Approval/Ask to validate"
    INFORMATIONAL = "Informational"
    OTHERS = "Others"
