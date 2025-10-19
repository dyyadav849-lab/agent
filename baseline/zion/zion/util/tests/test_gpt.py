from zion.agent.model import GrabGPTChatModelEnum
from zion.util.gpt import get_model_chunk_size, get_model_token_limit


def test_get_model_chunk_size() -> None:
    # Test with model_name = "GPT_4_o"
    model_name = GrabGPTChatModelEnum.AZURE_GPT4O
    expected_result = int(128000 * 0.9) * 3.2
    assert get_model_chunk_size(model_name) == expected_result

    # Test with default
    model_name = "model"
    expected_result = int(4096 * 0.9) * 3.2
    assert get_model_chunk_size(model_name) == expected_result


def test_get_model_token_limit() -> None:
    # Test with default
    model_name = "model"
    expected_result = int(4096 * 0.9)
    assert get_model_token_limit(model_name) == expected_result
