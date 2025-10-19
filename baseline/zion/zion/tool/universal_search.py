from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional, TypedDict

if TYPE_CHECKING:
    from datetime import datetime

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
from zion.util import helix
from zion.util.constant import DocumentTitle, DocumentUri
from zion.util.helix import SERVICE_ACCOUNT_NAME

HTTP_OK_STATUS = "OK"

KENDRA_RESULT_FAQ_TYPE = "QUESTION_ANSWER"
FAQ_QUESTION_KEY = "QuestionText"
FAQ_ANSWER_KEY = "AnswerText"


class KendraSearchStrategy(str, Enum):
    """Kendra search strategies"""

    Query = "query"
    Retrieve = "retrieve"

    def __str__(self) -> str:
        return str(self.value)


class KendraFilterKey(str, Enum):
    """Kendra filter keys"""

    ConfluenceSpace = "cf_space_name"
    HelixEntity = "entity_name"
    Category = "_category"

    def __str__(self) -> str:
        return str(self.value)


class KendraFilterCategory(str, Enum):
    """Kendra filter categories"""

    WikiDocs = "Wiki documents"
    HelixDocs = "Helix documents"
    GoogleDocs = "Google Docs"
    HelixEntities = "Helix entities"
    Videos = "Videos"

    def __str__(self) -> str:
        return str(self.value)


class SearchInput(BaseModel):
    query: str = Field(description="search query to search internal documentation")


class KendraQueryResultItem(TypedDict):
    DocumentURI: str
    DocumentId: str
    DocumentTitle: dict[str, Any]
    DocumentAttributes: list[dict[str, Any]]
    DocumentExcerpt: dict[str, Any]
    AdditionalAttributes: list[dict[str, Any]]
    Type: str
    ScoreAttributes: dict[str, Any]
    Content: str


class KendraQueryRes(TypedDict):
    ResultItems: list[KendraQueryResultItem]


class KendraRetrieveResultItem(TypedDict):
    DocumentURI: str
    DocumentId: str
    DocumentTitle: str
    DocumentAttributes: list[dict[str, Any]]
    AdditionalAttributes: list[dict[str, Any]]
    Type: str
    ScoreAttributes: dict[str, Any]
    Content: str


class KendraRetrieveRes(TypedDict):
    ResultItems: list[KendraRetrieveResultItem]


class KendraDocumentAttributeValue(BaseModel):
    StringValue: Optional[str]
    StringlistValue: Optional[list[str]]
    DateValue: Optional[datetime]
    LongValue: Optional[int]


class KendraDocumentAttribute(BaseModel):
    Key: Optional[str]
    Value: Optional[KendraDocumentAttributeValue]


class KendraAttributeFilter(BaseModel):
    AndAllFilters: Optional[list[KendraAttributeFilter]]
    OrAllFilters: Optional[list[KendraAttributeFilter]]
    ContainsAll: Optional[KendraDocumentAttribute]
    ContainsAny: Optional[KendraDocumentAttribute]
    EqualsTo: Optional[KendraDocumentAttribute]
    GreaterThan: Optional[KendraDocumentAttribute]
    GreaterThanOrEquals: Optional[KendraDocumentAttribute]
    LessThan: Optional[KendraDocumentAttribute]
    LessThanOrEquals: Optional[KendraDocumentAttribute]
    NotFilter: Optional[KendraAttributeFilter]


class UniversalSearchMetadata(BaseModel):
    """For reference only, it's not used because metadata is a dict in the BaseTool class"""

    AttributeFilter: KendraAttributeFilter | None = None
    """Filter the search results based on the document attributes. For example, filter the search results to only include documents that are of a specific type or have a specific tag."""

    PageSize: int | None = None
    """Override the default page size for the search results"""

    SearchFAQ: bool | None = None
    """Flag to search FAQ as additional context"""

    SearchHelixEntities: bool | None = None
    """Flag to search Helix entities as additional context"""


class UniversalSearchTool(BaseTool):
    name: str = "universal_search"
    description: str = general_search_tool_desc
    args_schema: type[BaseModel] = SearchInput
    handle_tool_error: bool = True  # handle ToolExceptions
    metadata: Optional[dict[str, Any]] = None

    def get_faq_document(self, result_item: KendraQueryResultItem) -> Document:
        """Construct Document object for the Kendra FAQ result item"""
        question = ""
        answer = ""

        for attribute in result_item["AdditionalAttributes"]:
            if attribute["Key"] == FAQ_QUESTION_KEY:
                question = attribute["Value"]["TextWithHighlightsValue"]["Text"]
            elif attribute["Key"] == FAQ_ANSWER_KEY:
                answer = attribute["Value"]["TextWithHighlightsValue"]["Text"]

        if not question or not answer:
            logger.warn(f"FAQ document missing question or answer: {result_item}")
            return Document()

        return Document(
            page_content=answer,
            metadata={
                DocumentTitle: question,
                DocumentUri: result_item["DocumentURI"],
            },
        )

    def query_faqs_res_to_documents(
        self, kendra_response: KendraQueryRes
    ) -> list[dict[str, Any]]:
        """Convert FAQs in query response to the dictionary representation of the Document objects"""
        return [
            self.get_faq_document(result_item).__dict__
            for result_item in kendra_response["ResultItems"]
            if result_item["Type"] == KENDRA_RESULT_FAQ_TYPE
        ]

    def query_res_to_documents(
        self, kendra_response: KendraQueryRes
    ) -> list[dict[str, Any]]:
        """Convert query response to the dictionary representation of the Document objects, to ensure it can be serialized to correct raw JSON"""
        return [
            Document(
                page_content=result_item["DocumentExcerpt"]["Text"],
                metadata={
                    DocumentTitle: result_item["DocumentTitle"]["Text"],
                    DocumentUri: result_item["DocumentURI"],
                },
            ).__dict__
            for result_item in kendra_response["ResultItems"]
        ]

    def retrieve_res_to_documents(
        self, kendra_response: KendraRetrieveRes
    ) -> list[dict[str, Any]]:
        """Convert retrieve response to the dictionary representation of the Document objects, to ensure it can be serialized to correct raw JSON"""
        return [
            Document(
                page_content=result_item["Content"],
                metadata={
                    DocumentTitle: result_item["DocumentTitle"],
                    DocumentUri: result_item["DocumentURI"],
                },
            ).__dict__
            for result_item in kendra_response["ResultItems"]
        ]

    def kendra_search(
        self,
        search_query: str,
        strategy: KendraSearchStrategy,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Used to search internal documentation for any additional context from Kendra"""

        try:
            concedo_token, helix_token = helix.get_helix_token()
        except ConnectionError as e:
            raise ToolException(str(e)) from e

        req_body = {
            "IndexId": global_config.kendra_index_id,
            "PageSize": 10,
            "QueryText": search_query,
            "PageNumber": 1,
            "UserContext": {"Token": f'{{"username":"{SERVICE_ACCOUNT_NAME}"}}'},
        }

        if metadata is not None:
            if metadata.get("AttributeFilter") is not None:
                req_body["AttributeFilter"] = metadata["AttributeFilter"]

            if metadata.get("PageSize") is not None:
                req_body["PageSize"] = metadata["PageSize"]

            if metadata.get("PageNumber") is not None:
                req_body["PageNumber"] = metadata["PageNumber"]

        res = requests.post(
            url=f"{global_config.helix_base_url}/api/kendra/{strategy}",
            data=json.dumps(req_body),
            headers={
                "x-auth-concedo-token": concedo_token,
                "Authorization": f"Bearer {helix_token}",
                "Content-Type": "application/json",
            },
            timeout=10,
        )

        if res.reason != HTTP_OK_STATUS:
            err_msg = f"Kendra search failed with status code `{res.status_code}` and reason `{res.reason}`, response: {res.text}"
            logger.error(err_msg)
            raise ToolException(err_msg)

        return res.json()

    def search_helix_entities(self, search_query: str) -> str:
        """This function is used to search Helix entities as additional context for the user query."""
        metadata = {
            "AttributeFilter": {
                "EqualsTo": {
                    "Key": str(KendraFilterKey.Category),
                    "Value": {"StringValue": str(KendraFilterCategory.HelixEntities)},
                }
            },
            "PageSize": 5,
        }
        return self.kendra_search(
            search_query=search_query,
            strategy=KendraSearchStrategy.Retrieve,
            metadata=metadata,
        )

    def search_docs(self, search_query: str) -> str:
        retrieve_doc_res = self.kendra_search(
            search_query=search_query,
            strategy=KendraSearchStrategy.Retrieve,
            metadata=self.metadata,
        )
        docs = self.retrieve_res_to_documents(retrieve_doc_res)

        if (
            self.metadata is not None
            and self.metadata.get("SearchHelixEntities") is True
        ):
            helix_entities_res = self.search_helix_entities(
                search_query=search_query,
            )
            docs += self.retrieve_res_to_documents(helix_entities_res)

        if self.metadata is not None and self.metadata.get("SearchFAQ") is True:
            # Note: FAQ only available in query strategy and they always return in the first page
            # Up to 4 FAQ documents will be returned
            faqs_res = self.kendra_search(
                search_query=search_query,
                strategy=KendraSearchStrategy.Query,
                metadata=self.metadata,
            )
            docs += self.query_faqs_res_to_documents(faqs_res)

        return json.dumps(docs)

    def _run(self, query: str, _: Optional[CallbackManagerForToolRun] = None) -> str:
        """Search internal documentation for additional context on user query"""
        return self.search_docs(search_query=query)

    async def _arun(
        self, query: str, _: Optional[AsyncCallbackManagerForToolRun] = None
    ) -> str:
        """Search internal documentation for additional context on user query asynchronously"""
        return self.search_docs(search_query=query)
