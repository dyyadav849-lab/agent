# ruff: noqa: SLF001, because we want to test the private method

import pytest
import requests_mock
from fastapi import HTTPException
from langchain_core.tools import ToolException
from requests import RequestException

from zion.config import global_config
from zion.tool.knowledge_base_search_tool import (
    KnowledgeBaseSearchTool,
    query_documents_api,
)


def test_query_knowledge_base_document() -> None:
    tool = KnowledgeBaseSearchTool(
        metadata={
            "knowledgebase_id": "test_knowledgebase_id",
            "count": 20,
        }
    )

    # Mock the requests.post call
    search_query = "test search query"
    mock_response = [
        {
            "page_content": "test page content",
            "metadata": {
                "title": "page title",
                "source": "https://test-source.com",
            },
            "type": "document",
        }
    ]

    with requests_mock.Mocker() as m:
        m.post(
            global_config.knowledge_base_service_base_url + query_documents_api,
            json=mock_response,
        )

        response = tool._query_knowledge_base_documents(search_query)

        # Check if it overrides the default count value
        assert m.last_request.json().get("count") == tool.metadata["count"]

        # Check if the response is a LangChain Document dict in string format
        assert (
            response
            == '[{"id": null, "metadata": {"document_title": "page title", "document_uri": "https://test-source.com"}, "page_content": "test page content", "type": "Document"}]'
        )


def test_query_knowledge_base_document_missing_metadata() -> None:
    tool = KnowledgeBaseSearchTool()

    # Check that it raises an HTTPException when metadata is missing
    with pytest.raises(HTTPException):
        tool._query_knowledge_base_documents("test search query")


def test_query_knowledge_base_document_request_exception() -> None:
    tool = KnowledgeBaseSearchTool(
        metadata={"knowledgebase_id": "test_knowledgebase_id"}
    )

    # Mock the requests.post call to raise a RequestException
    with requests_mock.Mocker() as m:
        m.post(
            global_config.knowledge_base_service_base_url + query_documents_api,
            exc=RequestException,
        )

        # Check that it raises a ToolException when RequestException is raised
        with pytest.raises(ToolException):
            tool._query_knowledge_base_documents("test search query")
