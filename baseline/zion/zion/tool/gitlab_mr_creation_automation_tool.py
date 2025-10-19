import asyncio
from typing import Optional

from langchain.callbacks.manager import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from zion.agent.constant import CREATE_MR_PROMPT
from zion.agent.model import ChatGrabGPT, GrabGPTEnum
from zion.agent.mr_creation_automation_agent import (
    create_mr_creation_automation_agent_node,
)
from zion.config import global_config
from zion.tool.util import get_prompt


class GitlabMrCreationAutomationInput(BaseModel):
    query: str = Field(description="Query input by the user")
    chat_history: list[str] = Field(description="Chat history in the slack message")


class GitlabMrCreationAutomationTool(BaseTool):
    name: str = "gitlab_mr_creation_automation"
    description: str = "Helps user to create a new MR only if user has requested."
    args_schema: type[BaseModel] = GitlabMrCreationAutomationInput
    handle_tool_error: bool = True  # handle ToolExceptions

    async def _execute_mr_creation(self, query: str, chat_history: list[str]) -> str:
        """Execute the MR creation process"""
        chat_grabgpt_data = {
            "api_key": global_config.openai_api_key,
            "base_url": f"{global_config.openai_endpoint}{GrabGPTEnum.UNIFIED_ENDPOINT_V1}",
            "model_name": self.metadata["model_name"],
            "temperature": 0,
            "timeout": 300,
        }
        model = ChatGrabGPT(model=chat_grabgpt_data["model_name"], **chat_grabgpt_data)
        query_source = self.metadata["query_source"]

        result = await create_mr_creation_automation_agent_node(
            model=model,
            prompt=get_prompt("create-mr-prompt", CREATE_MR_PROMPT),
            query_source=query_source,
            query=query,
            chat_history=chat_history,
        )

        # Return the response content and MR link
        return f"Message: {result.messages} \nMR Link: {result.mr_link}"

    def _run(
        self,
        query: str,
        chat_history: list[str],
        _: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Synchronous execution of the tool"""
        return asyncio.run(self._execute_mr_creation(query, chat_history))

    async def _arun(
        self,
        query: str,
        chat_history: list[str],
        _: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        """Asynchronous execution of the tool"""
        return await self._execute_mr_creation(query, chat_history)
