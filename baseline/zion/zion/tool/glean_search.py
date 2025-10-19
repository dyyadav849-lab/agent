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
from zion.tool.constant import general_search_tool_desc
from zion.util.constant import DocumentTitle, DocumentUri

HTTP_OK_STATUS = "OK"

# glean filter types
GLEAN_CONFLUENCE_FILTER = "confluence"
GLEAN_GDRIVE_FILTER = "gdrive"
GLEAN_JIRA_FILTER = "jira"


# type of document returned
GLEAN_GDRIVE_DOCUMENT = "Document"
GLEAN_GDRIVE_PRESENTATION = "Presentation"
GLEAN_GDRIVE_SPREADSHEET = "Spreadsheet"
GLEAN_GDRIVE_FOLDER = "Folder"

GLEAN_DOC_LIMIT = 50
SEARCH_SPACE_FILTER = 5


class SearchInput(BaseModel):
    query: str = Field(description="search query to search internal documentation")


class GleanRes:
    result_items: list[dict[str, Any]]
    valid_doc_taken: int = 0

    def __init__(self, result_item: any) -> None:
        self.result_items = []

        if "results" not in result_item:
            return

        result = result_item.get("results", [])
        for single_document_item in result:
            # must be within doc limit
            if self.valid_doc_taken >= GLEAN_DOC_LIMIT:
                break
            document_data = self.get_document(single_document_item)
            if self.is_valid_document(document_data):
                self.result_items.append(document_data.__dict__)
                self.valid_doc_taken += 1

    def is_valid_document(self, document_data: Document) -> bool:
        return (
            document_data.page_content != ""
            and document_data.metadata[DocumentUri] != ""
            and document_data.metadata[DocumentTitle] != ""
        )

    def get_document(self, document_returned: dict[str, Any]) -> Document:
        doc_content = ""

        for snippet_data in document_returned.get("snippets", []):
            text_data = snippet_data.get("text", "")
            if text_data != "":
                doc_content += f"\n{text_data}"

        return Document(
            page_content=doc_content,
            metadata={
                DocumentTitle: document_returned.get("title", ""),
                DocumentUri: document_returned.get("url", ""),
            },
        )


class GleanSearchTool(BaseTool):
    name: str = "glean_search"
    description: str = general_search_tool_desc
    args_schema: type[BaseModel] = SearchInput
    handle_tool_error: bool = True  # handle ToolExceptions
    metadata: Optional[dict[str, Any]] = None

    def _build_glean_request_body(
        self,
        search_query: str,
        techdocs_only: bool = False,  # noqa: FBT001, FBT002
    ) -> dict:
        """Used to build the glean search request body"""
        data_sources_filter = []
        facet_filter_wiki_space = []
        facet_techdocs_platform_name = []
        req_body_options = {
            "disableQueryAutocorrect": False,
        }

        if self.metadata is not None:
            if self.metadata.get("datasourcesFilter", None) is not None:
                data_sources_filter = self.metadata.get("datasourcesFilter")

            if self.metadata.get("wiki_space_collection", None) is not None:
                facet_filter_wiki_space = [
                    {"value": wiki_space, "relationType": "EQUALS"}
                    for wiki_space in self.metadata.get("wiki_space_collection")
                ]

            if self.metadata.get("techdocs_platform_name_collection", None) is not None:
                facet_techdocs_platform_name = [
                    {"value": techdocs_platform_name, "relationType": "EQUALS"}
                    for techdocs_platform_name in self.metadata.get(
                        "techdocs_platform_name_collection"
                    )
                ]

        if len(data_sources_filter) > 0 and not techdocs_only:
            # Only apply datasource filter for non-TechDocs searches (Confluence)
            # TechDocs searches don't use datasource
            new_data_sources_filter = [
                item for item in data_sources_filter if "techdocs" not in item
            ]
            req_body_options["datasourcesFilter"] = new_data_sources_filter

        req_body_options["facetFiltersSets"] = []
        if len(facet_filter_wiki_space) > 0 and not techdocs_only:
            req_body_options["facetFiltersSets"].append(
                {"fieldName": "space", "values": facet_filter_wiki_space}
            )

        if len(facet_techdocs_platform_name) > 0 and techdocs_only:
            req_body_options["facetFilter"] = {
                "fieldName": "platform",
                "values": facet_techdocs_platform_name,
            }

        return {
            "maxSnippetSize": 5000,
            "query": search_query,
            "pageSize": 50,
            "requestOptions": req_body_options,
        }

    def replace_glean_description(self, metadata: dict[str, Any]) -> None:
        """Used to replace glean description if user input custom description"""

        if metadata is not None and metadata.get("additional_metadata") is not None:
            additional_metadata = metadata.get("additional_metadata")
            if additional_metadata.get("custom_description", None) is not None:
                self.description = additional_metadata.get("custom_description")

    def glean_post_request(
        self,
        search_query: str,
        techdocs_only: bool = False,  # noqa: FBT001, FBT002
    ) -> list[dict[str, Any]]:
        """Used to search internal documentation for any additional context from Glean"""

        req_body = self._build_glean_request_body(search_query, techdocs_only)

        res = requests.post(
            url=f"{global_config.glean_base_url}/rest/api/v1/search",
            data=json.dumps(req_body),
            headers={"Authorization": f"Bearer {global_config.glean_bearer_token}"},
            timeout=20,
        )
        if res.reason != HTTP_OK_STATUS:
            err_msg = f"Glean search failed with status code `{res.status_code}` and reason `{res.reason}`, response: {res.text}"
            logger.error(err_msg)
            raise ToolException(err_msg)

        glean_results = GleanRes(res.json()).result_items

        # Remove results with https://wiki.grab.com/ URLs
        glean_results = [
            result
            for result in glean_results
            if not result.get("metadata", {})
            .get("document_uri", "")
            .startswith("https://wiki.grab.com/")
        ]

        # Post-filter results by space (Confluence)
        if (
            not techdocs_only
            and self.metadata
            and self.metadata.get("wiki_space_collection")
        ):
            allowed_spaces = self.metadata.get("wiki_space_collection")

            filtered_results = []
            for result in glean_results:
                # Get URL from metadata.document_uri
                url = result.get("metadata", {}).get("document_uri", "")

                if url:
                    # Check if URL contains the allowed space pattern
                    space_match = any(
                        f"/wiki/spaces/{space}/" in url for space in allowed_spaces
                    )
                    if space_match:
                        filtered_results.append(result)
                else:
                    # Keep results without URLs
                    filtered_results.append(result)

            return filtered_results

        # Post-filter results by platform (TechDocs)
        if (
            techdocs_only
            and self.metadata
            and self.metadata.get("techdocs_platform_name_collection")
        ):
            allowed_platforms = self.metadata.get("techdocs_platform_name_collection")

            filtered_results = []
            for result in glean_results:
                url = result.get("metadata", {}).get("document_uri", "")

                if url:
                    platform_match = any(
                        f"techdocs.grab.com/{platform}/" in url
                        or f"/{platform}/" in url
                        for platform in allowed_platforms
                    )
                    if platform_match:
                        filtered_results.append(result)
                else:
                    filtered_results.append(result)

            return filtered_results

        return glean_results

    def glean_search_tool(self, search_query: str) -> str:
        """Used to search internal documentation for any additional context from Glean"""

        techdocs_search = self.glean_post_request(search_query, techdocs_only=True)
        other_search = self.glean_post_request(search_query, techdocs_only=False)

        combine_search = (
            techdocs_search[:SEARCH_SPACE_FILTER] + other_search[:SEARCH_SPACE_FILTER]
        )

        return json.dumps(combine_search)

    def _run(self, query: str, _: Optional[CallbackManagerForToolRun] = None) -> str:
        """Search internal documentation for additional context on user query"""
        return self.glean_search_tool(query)

    async def _arun(
        self, query: str, _: Optional[AsyncCallbackManagerForToolRun] = None
    ) -> str:
        """Search internal documentation for additional context on user query asynchronously"""
        return self.glean_search_tool(query)
