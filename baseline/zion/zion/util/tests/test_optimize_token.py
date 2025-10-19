from langchain.schema import AIMessage, HumanMessage, SystemMessage
from langchain_core.documents import Document
from langchain_core.messages import (
    BaseMessage,
    ToolMessage,
)
from langchain_core.messages.ai import AIMessageChunk

from zion.agent.model import ChatGrabGPT, GrabGPTChatModelEnum
from zion.config import global_config
from zion.util.gpt import (
    get_model_token_limit,
)
from zion.util.optimize_token import (
    OptimizeDocumentResultToken,
    OptimizeMessageToken,
    is_contain_function_call,
    is_conversation_message,
    is_message_document_result,
)


def test_get_longest_document() -> None:
    # Test with empty list of documents
    documents = []

    chat_grabgpt_data = {
        "api_key": global_config.openai_api_key,
        "base_url": global_config.openai_endpoint,
        "model_name": GrabGPTChatModelEnum.AZURE_GPT4O,
        "temperature": 0,
        "timeout": 300,
    }
    model = ChatGrabGPT(model=GrabGPTChatModelEnum.AZURE_GPT4O, **chat_grabgpt_data)

    optimize_search_result = OptimizeDocumentResultToken(
        chat_open_ai=model,
        max_token=100,
    )

    result = optimize_search_result.get_longest_document(documents)
    assert result == (None, -1)

    # Test with single document
    document = Document(
        page_content="This is a document.",
    )
    documents = [document]
    result, _ = optimize_search_result.get_longest_document(documents)

    assert result.page_content == "This is a document."

    # Test with multiple documents
    document1 = Document(
        page_content="This is a short document.",
    )
    document2 = Document(
        page_content="This is a longer document.",
    )
    document3 = Document(
        page_content="This is the longest document.",
    )
    documents = [document1, document2, document3]
    result, _ = optimize_search_result.get_longest_document(documents)
    assert result.page_content == "This is the longest document."

    # Test with documents of equal length
    document1 = Document(
        page_content="This is a document.",
    )
    document2 = Document(
        page_content="This is also a document.",
    )
    documents = [document1, document2]
    result, _ = optimize_search_result.get_longest_document(documents)
    assert result.page_content == "This is also a document."


def test_is_message_document_result() -> None:
    # Test with message that is not a kendra search or glean search
    message = BaseMessage(content="This is a regular message", type="message")
    result = is_message_document_result(message)
    assert result is False

    # Test with message that is a kendra search
    message = BaseMessage(
        content="Perform kendra search",
        additional_kwargs={
            "name": "universal_search",
            "type": "tool",
        },
        type="tool",
    )
    result = is_message_document_result(message)
    assert result is True

    # Test with message that is a glean search
    message = BaseMessage(
        content="Perform glean search",
        additional_kwargs={
            "name": "glean_search",
            "type": "tool",
        },
        type="tool",
    )
    result = is_message_document_result(message)
    assert result is True

    # Test with message that gets document content
    message = BaseMessage(
        content="Get document content",
        additional_kwargs={
            "name": "get_document_content",
            "type": "tool",
        },
        type="tool",
    )
    result = is_message_document_result(message)
    assert result is True


def test_is_contain_function_call() -> None:
    # Test with empty list of messages
    messages = []
    result = is_contain_function_call(messages)
    assert result is False

    # Test with single message that is not an internal search
    message = BaseMessage(content="This is a regular message", type="message")
    messages = [message]
    result = is_contain_function_call(messages)
    assert result is False

    # Test with single message that is an internal search
    message = ToolMessage(
        content="Perform kendra search",
        additional_kwargs={
            "name": "universal_search",
            "type": "tool",
        },
        type="tool",
        tool_call_id="",
    )
    messages = [message]
    result = is_contain_function_call(messages)
    assert result is True

    # Test with multiple messages, some of which are internal searches
    message1 = BaseMessage(content="This is a regular message", type="message")
    message2 = ToolMessage(
        content="Perform kendra search",
        additional_kwargs={
            "name": "universal_search",
            "type": "tool",
        },
        type="tool",
        tool_call_id="",
    )
    message3 = ToolMessage(
        content="Perform glean search",
        additional_kwargs={
            "name": "glean_search",
            "type": "tool",
        },
        type="tool",
        tool_call_id="",
    )
    messages = [message1, message2, message3]
    result = is_contain_function_call(messages)
    assert result is True


def test_is_conversation_message() -> None:
    # Test with message that is not a conversation message
    message = SystemMessage(content="This is a regular message")
    result = is_conversation_message(message)
    assert result is False

    # Test with message that is a human message
    message = HumanMessage(content="This is a human message")
    result = is_conversation_message(message)
    assert result is True

    # Test with message that is an AI message
    message = AIMessage(content="This is an AI message")
    result = is_conversation_message(message)
    assert result is True

    # Test with message used to invoke function call
    message = AIMessageChunk(content="")
    result = is_conversation_message(message)
    assert result is False


def test_optimize_message_token() -> None:
    model_name = GrabGPTChatModelEnum.AZURE_GPT4O
    chat_grabgpt_data = {
        "api_key": global_config.openai_api_key,
        "base_url": global_config.openai_endpoint,
        "model_name": model_name,
        "temperature": 0,
        "timeout": 300,
    }
    model = ChatGrabGPT(model=model_name, **chat_grabgpt_data)
    optimize_message_token = OptimizeMessageToken(
        chat_open_ai=model, max_token=get_model_token_limit(model_name)
    )

    message_exceeding_limit = " ".join(["this"] * get_model_token_limit(model_name))

    # test 1: Test that should not optimize other than human and ai message
    messages: list[BaseMessage] = [
        SystemMessage(
            content=message_exceeding_limit,
        ),
        SystemMessage(
            content=message_exceeding_limit,
        ),
    ]
    messages_returned = optimize_message_token.optimize_token(messages=messages)

    assert messages_returned == messages

    system_message = SystemMessage(
        content="You are a slack answer assistant",
    )

    # test 2: Test that it should optimize and and only keep the last message
    final_human_message = HumanMessage(content="What is TI Bot?")
    messages: list[BaseMessage] = [
        system_message,
        HumanMessage(
            content="What is grab kit",
        ),
        AIMessage(
            content="GrabKit is a tool used in Grab's engineering ecosystem for creating and maintaining services.",
        ),
        HumanMessage(
            content="What is grab kit again",
        ),
        AIMessage(content=message_exceeding_limit),
        final_human_message,
    ]
    messages_returned = optimize_message_token.optimize_token(messages=messages)

    message_expected: list[BaseMessage] = [system_message, final_human_message]

    assert messages_returned == message_expected

    # test 3: Test that it should optimize and and only keep the last 3 messages
    trailing_user_messages: list[BaseMessage] = [
        HumanMessage(
            content="What is grab kit again",
        ),
        AIMessage(
            content="GrabKit is a tool used in Grab's engineering ecosystem for creating and maintaining services.",
        ),
        HumanMessage(
            content="What is TI Bot?",
        ),
    ]
    messages: list[BaseMessage] = [
        system_message,
        HumanMessage(
            content="What is grab kit",
        ),
        AIMessage(
            content=message_exceeding_limit,
        ),
        *trailing_user_messages,
    ]

    message_expected: list[BaseMessage] = [system_message, *trailing_user_messages]

    messages_returned = optimize_message_token.optimize_token(messages=messages)

    assert messages_returned == message_expected
