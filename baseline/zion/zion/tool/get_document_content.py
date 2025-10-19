import json
from typing import Any, Callable, ClassVar, Literal, Optional

from langchain.callbacks.manager import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain.tools import BaseTool
from langchain_core.documents import Document
from langchain_core.tools import ToolException
from pydantic import BaseModel, Field

from zion.config import logger
from zion.tool.glean_listshortcuts import GleanListshortcutsTool
from zion.util.get_url_metadata.confluence import ExtractConfluenceDocument
from zion.util.get_url_metadata.get_doc_type import DocumentType, get_doc_type
from zion.util.get_url_metadata.google_doc import get_google_doc_document
from zion.util.get_url_metadata.helix import (
    ExtractHelixEntityMetadata,
    ExtractHelixTechdocsContent,
)


class GetDocumentContentInput(BaseModel):
    document_url: str = Field(
        description="the document url to get document content from."
    )


class GetDocumentContentTool(BaseTool):
    name: str = "get_document_content"
    description: str = "Used to get document content for document links that has lack of context, or for document links that are attached by user in their messages"
    args_schema: type[BaseModel] = GetDocumentContentInput
    handle_tool_error: bool = True  # handle ToolExceptions
    doc_type_getter: ClassVar[
        dict[Literal[DocumentType.ConfluenceDocument], Callable[[str], Document]]
    ] = {
        DocumentType.ConfluenceDocument: ExtractConfluenceDocument().get_confluence_doc_document,
        DocumentType.GoogleDocument: get_google_doc_document,
        DocumentType.HelixDocument: ExtractHelixTechdocsContent().get_helix_techdocs_content,
        DocumentType.HelixEntity: ExtractHelixEntityMetadata().get_entity_metadata,
    }

    def get_document_content_tool(self, document_url: str) -> dict[str, Any]:
        """Used to get document content for document links that you need more context, or for document links that are attached by user in their messages"""

        def raise_url_not_found() -> None:
            error = "URL not found!"
            raise ToolException(error)

        try:
            if document_url.startswith("go/"):
                glean = GleanListshortcutsTool()
                go_link_url = glean.glean_listshortcuts_tool(document_url)
                document_url = go_link_url.replace('"', "")

            if document_url == "":
                raise_url_not_found()

            doc_type = get_doc_type(document_url)

            document_data = self.doc_type_getter[doc_type](document_url)
        except Exception as e:
            err_message = f"Unable to get document content with exception: {e!s}"
            logger.exception(err_message)
            raise ToolException(err_message) from e

        return json.dumps([document_data.__dict__])

    def _run(
        self, document_url: str, _: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Used to get document content for document links that has lack of context, or for document links that are attached by user in their messages"""
        return self.get_document_content_tool(document_url)

    async def _arun(
        self, document_url: str, _: Optional[AsyncCallbackManagerForToolRun] = None
    ) -> str:
        """Used to get document content for document links that has lack of context, or for document links that are attached by user in their messages asyncrhonoously"""
        return self.get_document_content_tool(document_url)
