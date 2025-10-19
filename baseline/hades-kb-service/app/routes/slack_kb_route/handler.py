import json
from typing import Optional

from fastapi import Depends, Query

from app.core.dependencies import (
    get_ragslack,
    get_transformer_singleton,
)
from app.core.log.logger import Logger
from app.core.ragslack.client import RagSlackClient
from app.core.transformer.client import TransformerClient
from app.models.azure_openai_model import (
    GrabGPTOpenAIModel,
)
from app.routes.slack_kb_route.models import (
    ConversationDetails,
    InsertRequestModel,
    InsertResponseModel,
    KnowledgeBaseRequestModel,
    KnowledgeBaseResponseModel,
    SlackMessage,
    SlackMessagesResponseModel,
)
from app.routes.utils import get_exception_action_response

logger = Logger(name="slack_kb_route_handler")


def knowledge_base_handler(
    request_input: KnowledgeBaseRequestModel,
    transformer: TransformerClient = Depends(get_transformer_singleton),
    ragslack: RagSlackClient = Depends(get_ragslack),
) -> KnowledgeBaseResponseModel:
    response = KnowledgeBaseResponseModel()

    try:
        ragslack.init_embedding_model(GrabGPTOpenAIModel.ADA_002)
        knowledge_search_result = ragslack.knowledge_base_search(request_input, "<#>")

        if len(knowledge_search_result) == 0:
            response.message = "No result is found"
            return response

        slack_information_result, pagination_result = ragslack.read_slack_information(
            knowledge_base_result=knowledge_search_result,
            filter_list=request_input.filter,
            limit=request_input.limit,
            page=request_input.page,
        )

        response.result = (
            (
                [
                    ConversationDetails(
                        slack_url=transformer.generate_slack_url(
                            result.channel_id, result.main_thread_ts
                        ),
                        chat_history=json.dumps(result.chat_history),
                        chat_summary=result.chat_summary,
                        updated_time=result.updated_at,
                    )
                    for result in slack_information_result
                ]
            )
            if len(slack_information_result) != 0
            else []
        )

        response.pagination = pagination_result

        return response  # noqa: TRY300: Redundant to put this statement to an else block

    except Exception as e:  # noqa: BLE001: blindly exception error, not blindly, handled with logging.
        response.message = "Knowledge base query error."
        return get_exception_action_response(
            e=e, logger=logger, name=knowledge_base_handler.__name__, response=response
        )


def insert_handler(
    request_input: InsertRequestModel,
    ragslack: RagSlackClient = Depends(get_ragslack),
) -> InsertResponseModel:
    response = InsertResponseModel()
    try:
        slack_information_doc = ragslack.insert_slack_information_to_db(request_input)

        if slack_information_doc.is_embedded:
            response.details = "Ingestion: Summary is previously embeded"
            return response

        ragslack.init_embedding_model(GrabGPTOpenAIModel.ADA_002)

        text_list = ragslack.text_pre_processing(
            text=request_input.chat_summary,
            splitter_selector=request_input.splitter_selector,
            chunk_size=request_input.chunk_config.chunk_size,
            chunk_overlap=request_input.chunk_config.chunk_overlap,
        )

        ragslack.insert_embeded_to_db(text_list, slack_information_doc)

        return response  # noqa: TRY300: Redundant to put this statement to an else block

    except (
        Exception  # noqa: BLE001: blindly exception error, not blindly, handled with logging.
    ) as e:
        error_tags = {
            "channel_id": request_input.channel_id,
            "main_thread_ts": request_input.main_thread_ts,
        }
        response.message = "Slack pgvector data ingestion error."
        return get_exception_action_response(
            e=e,
            logger=logger,
            name=insert_handler.__name__,
            response=response,
            tags=error_tags,
        )


async def get_slack_messages_handler(
    channel_id: Optional[str] = Query(None, description="Filter by channel ID"),
    limit: int = Query(10, ge=1, le=100, description="Number of messages to return"),
    offset: int = Query(0, ge=0, description="Number of messages to skip"),
    rag_slack_client: RagSlackClient = Depends(get_ragslack),
) -> SlackMessagesResponseModel:
    """Get slack messages with optional filtering"""
    logger.info(f"Getting slack messages for channel_id: {channel_id}, limit: {limit}, offset: {offset}")

    try:
        # Build filter conditions
        filter_conditions = []
        if channel_id:
            filter_conditions.append({"channel_id": [channel_id]})

        # Get messages and total count
        messages = rag_slack_client.get_slack_messages(filter_conditions, limit, offset)
        total_count = rag_slack_client.get_slack_messages_count(filter_conditions)

        # Convert to response model
        response_messages = [
            SlackMessage(
                channel_id=msg.channel_id,
                main_thread_ts=msg.main_thread_ts,
                chat_summary=msg.chat_summary,
                chat_history=msg.chat_history,
                created_at=msg.created_at,
                updated_at=msg.updated_at
            )
            for msg in messages
        ]

        return SlackMessagesResponseModel(
            messages=response_messages,
            total_count=total_count,
            limit=limit,
            offset=offset
        )

    except Exception as e:
        logger.error(f"Failed to get slack messages: {e}")
        raise
