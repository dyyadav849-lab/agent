from langchain.schema import BaseMessage, HumanMessage


def transform_chat_history(chat_history: list[BaseMessage]) -> list[BaseMessage]:
    """Append the `username` in front of content of each HumanMessage in the chat history."""

    # make a copy of the chat history
    _chat_history = chat_history.copy()

    for i, message in enumerate(_chat_history):
        if isinstance(message, HumanMessage):
            try:
                username = message.username
            except AttributeError:
                username = None

            if username:
                _chat_history[i].content = f"{message.username}: {message.content}"

    return _chat_history
