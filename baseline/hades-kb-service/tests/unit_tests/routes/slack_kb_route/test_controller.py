from copy import deepcopy
from typing import Tuple

import pytest
from fastapi.testclient import TestClient

from app.routes.slack_kb_route.handler import insert_handler, knowledge_base_handler
from app.routes.slack_kb_route.models import (
    InsertRequestModel,
    InsertResponseModel,
    KnowledgeBaseRequestModel,
    KnowledgeBaseResponseModel,
)
from app.server import app

bad_request_code = 400


def get_valid_insert_request() -> InsertRequestModel:
    return InsertRequestModel(
        chat_summary="Test summary",
        channel_id="ABC1234",
        main_thread_ts="12345.123456",
    )


def get_insert_request_test_cases() -> list[Tuple[int, InsertRequestModel]]:
    valid_request = get_valid_insert_request()

    empty_thread_ts = deepcopy(valid_request)
    empty_thread_ts.main_thread_ts = ""

    empty_chat_summary = deepcopy(valid_request)
    empty_chat_summary.chat_summary = ""

    empty_channel_id = deepcopy(valid_request)
    empty_channel_id.channel_id = ""

    negative_chunk_size = deepcopy(valid_request)
    negative_chunk_size.chunk_config.chunk_size = -1
    negative_chunk_size.chunk_config.chunk_overlap = -2

    negative_chunk_overlap = deepcopy(valid_request)
    negative_chunk_overlap.chunk_config.chunk_overlap = -1

    float_chunk_size = deepcopy(valid_request)
    float_chunk_size.chunk_config.chunk_size = 1.2

    float_chunk_overlap = deepcopy(valid_request)
    float_chunk_overlap.chunk_config.chunk_overlap = 1.2

    overlap_more_than_size = deepcopy(valid_request)
    overlap_more_than_size.chunk_config.chunk_size = 2
    overlap_more_than_size.chunk_config.chunk_overlap = 3

    multiple_wrong_field_value = deepcopy(valid_request)
    multiple_wrong_field_value.chunk_config.chunk_size = -1
    multiple_wrong_field_value.chat_history = ""
    multiple_wrong_field_value.chat_summary = ""

    return [
        (200, valid_request),
        (422, empty_chat_summary),
        (422, empty_thread_ts),
        (422, empty_channel_id),
        (200, negative_chunk_size),
        (200, negative_chunk_overlap),
        (422, float_chunk_size),
        (422, float_chunk_overlap),
        (422, overlap_more_than_size),
        (422, multiple_wrong_field_value),
    ]


def get_valid_knowledge_base_request() -> KnowledgeBaseRequestModel:
    return KnowledgeBaseRequestModel(query="Test query")


def get_knowledge_base_request_test_cases() -> (
    list[Tuple[int, KnowledgeBaseRequestModel]]
):
    valid_request = get_valid_knowledge_base_request()

    no_query_request = deepcopy(valid_request)
    no_query_request.query = ""

    vector_threshold_more_than_one = deepcopy(valid_request)
    vector_threshold_more_than_one.vector_threshold = 2

    vector_threshold_less_than_zero = deepcopy(valid_request)
    vector_threshold_less_than_zero.vector_threshold = -2

    vector_threshold_equal_one = deepcopy(valid_request)
    vector_threshold_equal_one.vector_threshold = 1

    vector_threshold_equal_zero = deepcopy(valid_request)
    vector_threshold_equal_zero.vector_threshold = 0

    page_is_not_digit = deepcopy(valid_request)
    page_is_not_digit.page = 1.2

    page_is_less_than_one = deepcopy(valid_request)
    page_is_less_than_one.page = -1

    invalid_filter = deepcopy(valid_request)
    invalid_filter.filter = {"exxample_for_testing": 1}

    return [
        (200, valid_request),
        (422, no_query_request),
        (422, vector_threshold_more_than_one),
        (422, vector_threshold_less_than_zero),
        (200, vector_threshold_equal_one),
        (200, vector_threshold_equal_zero),
        (422, page_is_not_digit),
        (422, page_is_less_than_one),
        (422, invalid_filter),
    ]


def insert_handler_mock(_: InsertRequestModel) -> InsertResponseModel:
    return InsertResponseModel()


def knowledge_base_handler_mock(
    _: KnowledgeBaseRequestModel,
) -> KnowledgeBaseResponseModel:
    return KnowledgeBaseResponseModel()


@pytest.mark.parametrize("expected, request_input", get_insert_request_test_cases())  # noqa: PT006: Not applicable
def test_slack_kb_route_insert_request(
    expected: str, request_input: InsertRequestModel
) -> None:  # : placeholder
    app.dependency_overrides[insert_handler] = insert_handler_mock
    client = TestClient(app)
    response = client.post("/slack/chathistory/insert", json=request_input.model_dump())
    assert expected == response.status_code


def test_slack_kb_route_insert_bad_request() -> None:
    request_input = get_valid_insert_request()
    client = TestClient(app)
    response = client.post("/slack/chathistory/insert", data=request_input)
    assert response.status_code == bad_request_code


@pytest.mark.parametrize(
    "expected, request_input",  # noqa: PT006: Not applicable
    get_knowledge_base_request_test_cases(),
)
def test_slack_kb_route_knowledge_base_request(
    expected: str, request_input: KnowledgeBaseRequestModel
) -> None:
    app.dependency_overrides[knowledge_base_handler] = knowledge_base_handler_mock
    client = TestClient(app)
    response = client.post(
        "/slack/chathistory/knowledgebase", json=request_input.model_dump()
    )
    assert expected == response.status_code


def test_slack_kb_route_knowledge_base_bad_request() -> None:
    request_input = get_valid_knowledge_base_request()
    client = TestClient(app)
    response = client.post("/slack/chathistory/knowledgebase", data=request_input)
    assert response.status_code == bad_request_code
