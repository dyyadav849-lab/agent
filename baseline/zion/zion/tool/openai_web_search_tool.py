from __future__ import annotations

import json
from typing import Any, Optional

import requests
from langchain.callbacks.manager import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain.tools import BaseTool
from langchain_core.tools import ToolException
from pydantic import BaseModel, Field

from zion.config import global_config, logger

HTTP_OK_STATUS = "OK"


class SearchInput(BaseModel):
    query: str = Field(description="search query for web search")


class OpenaiWebSearchTool(BaseTool):
    name: str = "openai_web_search"
    description: str = """Used for web searches (external sources) for comprehensive, accurate, and trusted results. Useful for when you need to answer questions about current events, real-time issues, up-to-date documentation on external libraries, etc. Responses will include inline citations for URLs found in the web search results."""
    args_schema: type[BaseModel] = SearchInput
    handle_tool_error: bool = True  # handle ToolExceptions
    metadata: Optional[dict[str, Any]] = None

    def openai_web_search_tool(self, search_query: str) -> str:
        """Used for web searches via ChatGPT search"""

        req_body = {
            "model": "openai/gpt-4o-search-preview",
            "messages": [
                {"role": "user", "content": search_query},
            ],
            "stream": False,
        }

        res = requests.post(
            url=f"{global_config.openai_endpoint}/unified/v1/chat/completions",
            data=json.dumps(req_body),
            headers={"api-key": f"{global_config.openai_api_key}"},
            timeout=30,
        )
        if res.reason != HTTP_OK_STATUS:
            err_msg = f"OpenAI web search failed with status code `{res.status_code}` and reason `{res.reason}`, response: {res.text}"
            logger.error(err_msg)
            raise ToolException(err_msg)

        return res.json()["choices"][0]["message"]["content"]

    def _run(self, query: str, _: Optional[CallbackManagerForToolRun] = None) -> str:
        """Search web for additional context on user query"""
        return self.openai_web_search_tool(query)

    async def _arun(
        self, query: str, _: Optional[AsyncCallbackManagerForToolRun] = None
    ) -> str:
        """Search web for additional context on user query asynchronously"""
        return self.openai_web_search_tool(query)
