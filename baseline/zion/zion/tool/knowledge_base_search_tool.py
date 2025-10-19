from __future__ import annotations

import json
from typing import Any, Optional, TypedDict

from fastapi import HTTPException
from langchain.callbacks.manager import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain.tools import BaseTool
from langchain_core.documents import Document
from langchain_core.tools import ToolException
from pydantic import BaseModel, Field
from requests import RequestException, post

from zion.config import global_config, logger
from zion.tool.constant import general_search_tool_desc
from zion.util.constant import DocumentTitle, DocumentUri

query_documents_api = "/api/v1/query/documents"
default_count = 10


class KnowledgeBaseSearchMetadata(TypedDict):
    title: str
    id: str
    source: str
    when: str
    knowledge_id: int


class KnowledgeBaseSearchDoc(TypedDict):
    page_content: str
    metadata: KnowledgeBaseSearchMetadata
    type: str


class KnowledgeBaseSearchInput(BaseModel):
    query: str = Field(description="search query to search knowledge base")


class KnowledgeBaseSearchTool(BaseTool):
    name: str = "knowledge_base_search"
    description: str = general_search_tool_desc
    args_schema: type[BaseModel] = KnowledgeBaseSearchInput
    handle_tool_error: bool = True  # handle ToolExceptions
    metadata: Optional[dict[str, Any]] = None

    def _convert_search_res_to_documents(
        self, res_body: list[KnowledgeBaseSearchDoc]
    ) -> list[dict[str, Any]]:
        """Convert search result to LangChain Document in dictionary format"""
        return [
            Document(
                page_content=result_item["page_content"],
                metadata={
                    DocumentTitle: result_item["metadata"]["title"],
                    DocumentUri: result_item["metadata"]["source"],
                },
            ).__dict__
            for result_item in res_body
        ]

    def _query_knowledge_base_documents(self, search_query: str) -> str:
        """Search knowledge base for additional context on user query"""

        if not self.metadata or not self.metadata.get("knowledgebase_id"):
            raise HTTPException(
                status_code=400,
                detail=f"knowledgebase_id is a required metadata field for {self.name} tool",
            )

        knowledgebase_id = self.metadata.get("knowledgebase_id") or ""

        try:
            res = post(
                url=global_config.knowledge_base_service_base_url + query_documents_api,
                json={
                    "knowledgebase_id": knowledgebase_id,
                    "question": search_query,
                    "count": self.metadata.get("count", default_count),
                },
                timeout=30,
            )
            res_body = self._convert_search_res_to_documents(res.json())
            return json.dumps(res_body)
        except RequestException as e:
            res_body_text = f"Failed to query knowledge base: {e!s}"
            logger.error(res_body_text)
            raise ToolException(res_body_text) from e

    def _run(self, query: str, _: Optional[CallbackManagerForToolRun] = None) -> str:
        """Search knowledge base for additional context on user query"""
        return self._query_knowledge_base_documents(search_query=query)

    async def _arun(
        self, query: str, _: Optional[AsyncCallbackManagerForToolRun] = None
    ) -> str:
        """Search knowledge base for additional context on user query asynchronously"""
        return self._query_knowledge_base_documents(search_query=query)
