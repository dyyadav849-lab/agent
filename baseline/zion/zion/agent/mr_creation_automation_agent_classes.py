from collections.abc import Sequence
from typing import Annotated

from langchain_core.messages import (
    BaseMessage,
)
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class MrCreationAgentState(TypedDict):
    """The state of the agent."""

    messages: Annotated[Sequence[BaseMessage], add_messages]
