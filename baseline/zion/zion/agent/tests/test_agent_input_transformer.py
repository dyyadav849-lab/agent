from langchain.schema import AIMessage, HumanMessage

from zion.agent.agent_input_transformer import transform_chat_history


def test_transform_chat_history() -> None:
    # Create a sample chat history

    chat_history = [
        HumanMessage(content="Hello", username="Alice", type="human"),
        AIMessage(content="Hi, How can I helped you?", username="AI", type="ai"),
        HumanMessage(content="I need help with my account", type="human"),
    ]

    # Call the function to transform the chat history
    transformed_history = transform_chat_history(chat_history)

    # Check if the transformation is correct
    assert transformed_history[0].content == "Alice: Hello"
    assert transformed_history[1].content == "Hi, How can I helped you?"
    assert transformed_history[2].content == "I need help with my account"
