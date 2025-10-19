from typing import Optional

from fastapi import APIRouter, Depends, Query, Request

from app.core.log.logger import Logger
from app.routes.slack_kb_route.handler import (
    get_slack_messages_handler,
    insert_handler,
    knowledge_base_handler,
)
from app.routes.slack_kb_route.models import (
    InsertResponseModel,
    KnowledgeBaseResponseModel,
    SlackMessagesResponseModel,
)
from app.routes.slack_kb_route.response_config import open_api_config

slack_kb_route = APIRouter()
logger = Logger(name="slack_kb_route_controller")


async def log_request(request: Request) -> None:
    body_info = await request.body()
    logger.info(message={"body": body_info, "headers": request.headers})


@slack_kb_route.post(
    "/slack/chathistory/insert",
    response_model=InsertResponseModel,
    responses=open_api_config,
)
async def insert_pg_vector_db(
    request: Request,
    result: InsertResponseModel = Depends(insert_handler),
) -> InsertResponseModel:
    await log_request(request)
    return result


@slack_kb_route.post(
    "/slack/chathistory/knowledgebase",
    response_model=KnowledgeBaseResponseModel,
    responses=open_api_config,
)
async def knowledge_base(
    request: Request,
    result: KnowledgeBaseResponseModel = Depends(knowledge_base_handler),
) -> KnowledgeBaseResponseModel:
    await log_request(request)
    return result


@slack_kb_route.get(
    "/slack/messages",
    response_model=SlackMessagesResponseModel,
    responses=open_api_config,
)
async def get_slack_messages(
    request: Request,
    channel_id: Optional[str] = Query(None, description="Filter by channel ID"),
    limit: int = Query(10, ge=1, le=100, description="Number of messages to return"),
    offset: int = Query(0, ge=0, description="Number of messages to skip"),
    result: SlackMessagesResponseModel = Depends(get_slack_messages_handler),
) -> SlackMessagesResponseModel:
    """Get slack messages from the last 24 hours with optional channel filtering"""
    await log_request(request)
    return result
