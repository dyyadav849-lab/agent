import pytest
import requests_mock
from langchain_core.tools import ToolException
from requests import RequestException

from zion.config import global_config
from zion.tool.constant import hades_kb_endpoint
from zion.tool.hades_kb_service import (
    HadesKnowledgeBaseTool,
    HadesKnowledgeBaseToolOutput,
)


@pytest.mark.parametrize(
    ("url", "mock_return"),
    [
        (
            global_config.hades_kb_service_base_url,
            HadesKnowledgeBaseToolOutput(result=[]),
        )
    ],
)
def test_get_similar_past_conversation(
    url: str, mock_return: HadesKnowledgeBaseToolOutput | None
) -> None:
    hades_http_client = HadesKnowledgeBaseTool()
    base_url = url
    with requests_mock.Mocker() as m:
        m.post(f"{base_url}{hades_kb_endpoint}", json=mock_return.dict())
        actual_data = hades_http_client.get_similar_past_conversation(query="hi")
        assert actual_data == "[]"


@pytest.mark.parametrize("url", [(global_config.hades_kb_service_base_url)])
def test_get_similar_past_conversation_error(url: str) -> None:
    hades_http_client = HadesKnowledgeBaseTool()
    base_url = url
    with requests_mock.Mocker() as m:
        m.post(f"{base_url}{hades_kb_endpoint}", exc=RequestException)

        with pytest.raises(ToolException):
            hades_http_client.get_similar_past_conversation(query="hi")
