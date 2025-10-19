import json
from datetime import datetime
from typing import Any, Optional

from langchain.tools import BaseTool
from langchain_core.documents import Document
from langchain_core.tools import ToolException
from pydantic import BaseModel, Field
from requests import RequestException

from zion.config import logger
from zion.tool.constant import hades_kb_endpoint
from zion.util.constant import DocumentTitle, DocumentUri
from zion.util.http_client.client import hades_http_client


class HadesServiceSearchInput(BaseModel):
    filter: Optional[dict[str, list[str]]] = Field(
        default=None, description="Filter criteria for the http-client"
    )
    query: str = Field(description="search query for pgvector database")
    limit: int = Field(
        default=5,
        description="Limit the return result, may specified based on need, default is 5, 0 return 422 error",
    )
    is_agent: bool = Field(
        default=True, description="True if the endpoint triggered by llm"
    )


class HadesKnowledgeBaseToolInput(BaseModel):
    query: str = Field(description="search query for pgvector database")


class ConversationDetails(BaseModel):
    slack_url: str = Field(description="slack_url for reference")
    chat_summary: str = Field(
        default="", description="Summary in chat form for input query context reference"
    )
    updated_time: datetime = Field(
        description="Date of data being ingested into knowledge base"
    )


class HadesKnowledgeBaseToolOutput(BaseModel):
    result: list[ConversationDetails] = Field(
        description="List of past conversation history, summary, and reference source (slack_url), based on the input query."
    )


class HadesKnowledgeBaseTool(BaseTool):
    name: str = "slack_conversation_tool"
    description: str = (
        "Contains previously resolved on-call Slack queries. The response is a list of documents where chat history is in page_content field and slack url in document_uri field. You MUST UNDERSTAND the whole chat history and summarise the chat history without cherry-picking a particular reply. For any chat history you use to generate the answer, you MUST return its unique slack url for user reference in this citation format '[[index]](<slack url>)'. The citation must be labelled with a meaningful title based on the summary."
        "The chat_history is provided in Document Schema."
        "If multiple chat histories share the same context, the latest one is chosen. All summaries are retained if contexts differ."
        "If chat histories consisting of unique identifiers match the user query, you must return them and use them as a 'reference source' even if you did not use them to answer."
        "For example, if `transaction id:123` is present in both the user query and chat histories, they are relevant."
    )
    args_schema: type[BaseModel] = HadesKnowledgeBaseToolInput
    handle_tool_error: bool = True
    metadata: Optional[dict[str, Any]] = None

    def _run(self, query: str) -> str:
        """Use the tool."""

        return self.get_similar_past_conversation(query=query)

    async def _arun(self, query: str) -> str:
        """Use the tool asynchronously."""

        return self.get_similar_past_conversation(query=query)

    def get_similar_past_conversation(self, query: str) -> str:
        original_query = ""
        if self.metadata is not None:
            original_query = self.metadata.get("user_prompt", "")

        hades_service_search_input = HadesServiceSearchInput(
            query=f"{query}. {original_query}"
        )

        payload = hades_service_search_input.dict()
        try:
            with hades_http_client.get_session() as session:
                response = hades_http_client.post(
                    session=session,
                    endpoint=hades_kb_endpoint,
                    json=payload,
                    headers={},
                )

                parse_response = HadesKnowledgeBaseToolOutput(**response).result

                document_list = [
                    Document(
                        page_content=result.chat_summary,
                        metadata={
                            DocumentTitle: result.slack_url,
                            DocumentUri: result.slack_url,
                        },
                    ).__dict__
                    for result in parse_response
                ]

                return json.dumps(document_list)

        except RequestException as e:
            res_body_text = f"Failed to query hades service: {e!s}"
            logger.error(res_body_text)
            raise ToolException(res_body_text) from e
