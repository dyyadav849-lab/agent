from __future__ import annotations

import json
from typing import Any, Optional

import requests
from langchain.callbacks.manager import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain.tools import BaseTool
from langchain_core.documents import Document
from langchain_core.tools import ToolException
from pydantic import BaseModel, Field

from zion.config import global_config, logger
from zion.util.constant import DocumentTitle, DocumentUri

HTTP_OK_STATUS = "OK"
DOCUMENT_KB_SEARCH_LIMIT = 10


class HadesDocumentKBSearchInput(BaseModel):
    query: str = Field(description="search query to search document knowledge base RAG")


class HadesDocumentKBSearchResult:
    result_items: list[dict[str, Any]]
    valid_doc_taken: int = 0

    def __init__(self, result_item: dict) -> None:
        self.result_items = []
        if "result" not in result_item:
            return

        result = result_item.get("result", [])
        for single_document_item in result:
            # must be within doc limit
            if self.valid_doc_taken >= DOCUMENT_KB_SEARCH_LIMIT:
                break

            document_data = self.get_document(single_document_item)
            if self.is_valid_document(document_data):
                self.result_items.append(document_data.__dict__)
                self.valid_doc_taken += 1

    def is_valid_document(self, document_data: Document) -> bool:
        return document_data.page_content != ""

    def get_document(self, document_returned: dict[str, Any]) -> Document:
        return Document(
            page_content=document_returned.get("document_embedding", {}).get(
                "text_snipplet", ""
            ),
            metadata={
                DocumentTitle: document_returned.get("document_information", {}).get(
                    "filename", ""
                ),
                DocumentUri: document_returned.get("document_information", {}).get(
                    "media_serve_file_path", ""
                ),
            },
        )


class HadesDocumentKBSearch(BaseTool):
    name: str = "rag_document_kb_search"
    description: str = """This tool is used for searching documentation knowledge base that was uploaded by user.
"""
    args_schema: type[BaseModel] = HadesDocumentKBSearchInput
    handle_tool_error: bool = True  # handle ToolExceptions
    metadata: Optional[dict[str, Any]] = None

    def __build_hades_document_kb_search_filter(self) -> list[str]:
        if (
            self.metadata is None
            or self.metadata.get("document_collection", None) is None
        ):
            err_msg = "Cannot search hades document kb tool due to error: 'document_collection' cannot be missing from tool metadata"
            raise ToolException(err_msg)

        return [
            document_collection.get("uuid", "")
            for document_collection in self.metadata.get("document_collection", [])
        ]

    def hades_document_kb_search_tool(self, search_query: str) -> str:
        """Used to search internal documentation for any additional context from Document KB Search"""

        res = requests.post(
            url=f"{global_config.hades_kb_service_base_url}/doc_kb_route/search_document_knowledge_base",
            data=json.dumps(
                {
                    "query": search_query,
                    "filter": {
                        "document_collection_uuids": self.__build_hades_document_kb_search_filter()
                    },
                },
            ),
            headers={
                "rag-document-secret": global_config.hades_document_rag_secret_key
            },
            timeout=20,
        )
        if res.reason != HTTP_OK_STATUS:
            err_msg = f"Hades Document KB search failed with status code `{res.status_code}` and reason `{res.reason}`, response: {res.text}"
            logger.error(err_msg)
            raise ToolException(err_msg)
        return json.dumps(HadesDocumentKBSearchResult(res.json()).result_items)

    def _run(self, query: str, _: Optional[CallbackManagerForToolRun] = None) -> str:
        """Search internal documentation for additional context on user query"""
        return self.hades_document_kb_search_tool(query)

    async def _arun(
        self, query: str, _: Optional[AsyncCallbackManagerForToolRun] = None
    ) -> str:
        """Search internal documentation for additional context on user query asynchronously"""
        return self.hades_document_kb_search_tool(query)
