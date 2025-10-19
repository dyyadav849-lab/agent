from datetime import datetime
from typing import Dict, Optional

from fastapi.exceptions import RequestValidationError
from pydantic import (
    BaseModel,
    Field,
    Json,
    model_validator,
)

from app.core.constant import query_limit
from app.core.transformer.text_splitter.models import text_splitter_mapper
from app.routes.utils import BaseResponse, is_float
from app.storage.ragslack_db.client import RagSlackDbClient


class KnowledgeBaseRequestModel(BaseModel):
    filter: Optional[Dict[str, list[str]]] = None
    query: str = ""
    limit: int = query_limit
    vector_threshold: float = 0.8
    page: int = 1
    is_agent: bool = False

    @model_validator(mode="before")
    @classmethod
    def validate_request_body(cls, value: dict) -> dict:
        message = "missing fields:"
        is_missing = False
        filter_dict = value.get("filter")
        limit = value.get("limit", 0)
        vector_threshold = value.get("vector_threshold", 0)
        page = value.get("page", 1)

        if not str(value.get("query", "")).strip():
            message = f"{message}{',' if is_missing else ''} query"
            is_missing = True

        if (
            not is_float(vector_threshold)
            or vector_threshold > 1
            or vector_threshold < 0
        ):
            message = f"{message}vector_threshold is not a float or not in range 0 to 1, {vector_threshold}"
            is_missing = True

        if not str(page).isdigit() or page < 1:
            message = f"{message}Page field can only be more than 0, {page}"
            is_missing = True

        if not str(limit).isdigit() or limit < 0:
            message = f"{message}limit is not a digit or not in range 0 to 1, {limit}"
            is_missing = True

        if not isinstance(value.get("is_agent", False), bool):
            message = f"{message} is_agent field given is not bool type"
            is_missing = True

        if is_missing:
            raise RequestValidationError(errors=f"{message} | request body: {value}")

        if filter_dict is not None:
            invalid_list = RagSlackDbClient.check_invalid_slack_filter_key(filter_dict)
            if len(invalid_list) > 0:
                error_message = f"Invlid filter key is provided in request body, invalid key list {invalid_list}"
                raise RequestValidationError(errors=f"{error_message}")

        return value


class ConversationDetails(BaseModel):
    slack_url: str = ""
    chat_history: Json = None
    chat_summary: str = ""
    updated_time: datetime

    class Config:
        orm_mode = True


class Pagination(BaseModel):
    total_items_count: int = 0
    page_size: int = 0
    current_page: int = 1
    total_page: int = 0


class KnowledgeBaseResponseModel(BaseResponse):
    result: list[ConversationDetails] = []
    pagination: Pagination = Pagination()


class ChatHistoryModel(BaseModel):
    text: str
    user: str


class ChunkConfiguration(BaseModel):
    chunk_size: int = 0
    chunk_overlap: int = 0


class InsertRequestModel(BaseModel):
    chat_history: list[ChatHistoryModel] = []
    chat_summary: str
    channel_id: str
    main_thread_ts: str
    splitter_selector: int = Field(default=1, description=str(text_splitter_mapper))
    chunk_config: ChunkConfiguration = ChunkConfiguration()

    @model_validator(mode="before")
    @classmethod
    def validate_request_body(cls, value: dict) -> dict:
        message = "missing fields:"
        is_missing = False
        chunk_config_label = "chunk_config"
        chunk_size_label = "chunk_size"
        chunk_overlap_label = "chunk_overlap"

        chunk_size = value.get(chunk_config_label, {}).get(chunk_size_label, 0)
        chunk_overlap = value.get(chunk_config_label, {}).get(chunk_overlap_label, 0)
        main_thread_ts = value.get("main_thread_ts", "")

        if chunk_overlap > chunk_size:
            raise RequestValidationError(
                errors=f"chunk overlap cannot be larger than chunk size, current config = chunk_overlap: {chunk_overlap} | chunk_size: {chunk_size}"
            )

        if chunk_size < 0:
            value[chunk_config_label][chunk_size_label] = 0

        if chunk_overlap < 0:
            value[chunk_config_label][chunk_overlap_label] = 0

        if not str(value.get("channel_id", "")).strip():
            message = f"{message}{',' if is_missing else ''} channel_id"
            is_missing = True

        if not is_float(main_thread_ts):
            message = f"main_thread_ts is not a digit, {main_thread_ts}"
            raise RequestValidationError(errors=f"{message} | request body: {value}")

        if not str(value.get("chat_summary", "")).strip():
            message = f"{message}{',' if is_missing else ''} chat_summary"
            is_missing = True

        if is_missing:
            raise RequestValidationError(errors=f"{message} | request body: {value}")

        return value


class InsertResponseModel(BaseResponse):
    pass


class SlackMessage(BaseModel):
    """Model for a single slack message"""
    channel_id: str
    main_thread_ts: str
    chat_summary: str
    chat_history: list
    created_at: datetime
    updated_at: datetime


class SlackMessagesResponseModel(BaseResponse):
    """Response model for slack messages endpoint"""
    messages: list[SlackMessage] = []
    total_count: int = 0
    limit: int = 10
    offset: int = 0
