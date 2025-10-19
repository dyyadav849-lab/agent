
from __future__ import annotations

from enum import Enum
from typing import Any

from langchain_core.runnables import (
    RunnableConfig,
)
from pydantic import BaseModel

from zion.agent.agent_builder import (
    BaseAgentInput,
    BaseAgentOutput,
)
from zion.config import AgentProfile
from zion.tool.agent_plugins import AgentPlugin
from zion.tool.agent_tool import ZionAgentActions


class AttributeInfo(BaseModel):
    description: str
    value_type: str


class AzureOpenAIConfig(BaseModel):
    azure_deployment: str | None = None
    model_name: str | None = None
    temperature: float | None = None
    timeout: int | None = None
    streaming: bool | None = None
    api_key: str | None = None


class AgentType(str, Enum):
    agent_executor = "agent_executor"
    """Uses the agent executor as the LLM Agent (now deprecated by Langsmith)"""

    react_agent = "react_agent"
    """Uses the react agent as the LLM Agent"""

    multi_agent = "multi_agent"
    """Uses the react multi-agent as the LLM Agent"""

    follow_up_convo_agent = "follow_up_convo_agent"
    """Uses the follow-up convo single agent as the LLM Agent"""


class MaskingMode(str, Enum):
    mask_info = "mask_info"
    """Only mask the input, chat_history and prompt, tool call sequence and token usages will still captured in the LangSmith run tracing."""

    hide_all = "hide_all"
    """Hide all info, tool call sequence and token usages WILL NOT be captured in the LangSmith run tracing."""

    off = "off"
    """Not hiding or mask any info"""

    def __str__(self) -> str:
        # when an instance is used in a string context, return the value
        return str(self.value)


class AgentTracing(BaseModel):
    hide_input: MaskingMode | None = MaskingMode.off
    """Mask inputs from the LangSmith run tracing. Default is `off` if not provided."""
    hide_output: MaskingMode | None = MaskingMode.off
    """Mask outputs from the LangSmith run tracing. Default is `off` if not provided."""
    tags: list[str] | None
    """Tags for the LangSmith run tracing"""


class AgentExecutorConfig(BaseModel):
    max_iterations: int = 15


class AgentConfig(BaseModel):
    tracing: AgentTracing | None = None
    plugins: list[AgentPlugin] | None = None
    llm_model: AzureOpenAIConfig | None = None
    agent_executor_config: AgentExecutorConfig | None = AgentExecutorConfig()
    agent_type: AgentType | None = AgentType.agent_executor
    trigger_guardrails: bool = True
    mcp_config: dict[str, Any] | None = None


class StructuredResponseSchema(BaseModel):
    obj: dict[str, AttributeInfo]


class QuerySource(BaseModel):
    username: str = ""
    channel_name: str = ""
    workflow_id: str = ""


class ZionAgentInput(BaseAgentInput):
    system_prompt: str | None = None
    system_prompt_hub_commit: str | None = None
    system_prompt_variables: dict[str, Any] | None = None
    structured_response_schema: dict[str, AttributeInfo] | None = None
    structured_response_schema_hub_commit: str | None = None
    agent_config: AgentConfig | None = AgentConfig()
    query_source: QuerySource | None = QuerySource()


class ZionAgentOutput(BaseAgentOutput):
    # Structured response is a dictionary of key-value pairs returned by the agent
    # which defined in ZionAgentInput's `structured_response_schema`
    structured_response: dict[str, Any] | None = None
    # Audit trail ID for Agent
    agent_execution_trail_id: int | None = None
    # Agent execution actions
    agent_actions: list[ZionAgentActions] | None = None
    # Langsmith run ID
    langsmith_run_id: str | None = None


class ZionRunnableConfig(RunnableConfig):
    agent_profile: AgentProfile
