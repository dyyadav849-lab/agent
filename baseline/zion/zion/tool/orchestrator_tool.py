from __future__ import annotations

from langchain.tools import BaseTool
from pydantic import BaseModel

from zion.agent.orchestrators_plugin import OrchestratorPluginConfig
from zion.data.agent_plugin.data import (
    AgentPlugin,
)


class OrchestratorToolInputSchema(BaseModel):
    """Schema for GetToolPrompt."""


class OrchestratorTool(BaseTool):
    name: str = "orchestrator_tool"
    description: str = """
    Use this tool to retrieve system prompt for selected tools/function call.
    System Prompt:
    """
    tool_prompt: str = ""
    args_schema: type[BaseModel] = OrchestratorToolInputSchema

    @classmethod
    def generate_orchestrator_plugin(
        cls: OrchestratorTool, plugin: AgentPlugin
    ) -> OrchestratorTool:
        orchestrator_plugin = OrchestratorPluginConfig(**plugin.orchestrators_plugin)

        orchestrator_config = orchestrator_plugin.orchestrator

        if (
            orchestrator_config is not None
            and orchestrator_config.action.lower() == "pre"
        ):
            # pre_(tool_name)_orchestrator_tool
            tool_prompt = orchestrator_config.prompt
            tool_name = (
                f"pre_{orchestrator_config.target_tool.strip()}_orchestrator_tool"
            )
            tool_description = f"You MUST use this tool to retrieve instruction on how to use {orchestrator_config.target_tool.strip()} tool."

        if (
            orchestrator_config is not None
            and orchestrator_config.action.lower() == "post"
        ):
            # post_(tool_name)_orchestrator_tool
            tool_prompt = orchestrator_config.prompt
            tool_name = (
                f"post_{orchestrator_config.target_tool.strip()}_orchestrator_tool"
            )
            tool_description = f"You MUST use this tool after using {orchestrator_config.target_tool.strip()} tool, it consists of instruction on how to utilize result from {orchestrator_config.target_tool.strip()} tool."

        return cls(
            tool_prompt=tool_prompt, name=tool_name, description=tool_description
        )

    def _run(
        self,
    ) -> str:
        return self.tool_prompt

    async def _arun(
        self,
    ) -> str:
        return self.tool_prompt
