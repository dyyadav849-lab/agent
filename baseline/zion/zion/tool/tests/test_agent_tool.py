from langchain_core.agents import AgentActionMessageLog
from langchain_core.messages import AIMessage, HumanMessage

from zion.tool.agent_tool import (
    INFO_MASKED,
    get_zion_agent_actions,
    mask_any_value,
    mask_inputs,
    mask_outputs,
)

langchain_intermediate_steps = [
    [
        AgentActionMessageLog(
            tool="requests_tool",
            tool_input={
                "http_method": "GET",
                "http_full_url_with_query": "https://api.openweathermap.org/data/2.5/weather?q=Kuala%20Lumpur&appid=YOUR_API_KEY",
            },
            log="\nInvoking: `requests_tool` with `{'http_method': 'GET', 'http_full_url_with_query': 'https://api.openweathermap.org/data/2.5/weather?q=Kuala%20Lumpur&appid=YOUR_API_KEY'}`\n\n\n",
            type="AgentActionMessageLog",
            message_log=[
                {
                    "content": "",
                    "additional_kwargs": {
                        "tool_calls": [
                            {
                                "index": 0,
                                "id": "call_ePbadmMIlKqtY43OA5Sq98WZ",
                                "function": {
                                    "arguments": '{"http_method":"GET","http_full_url_with_query":"https://api.openweathermap.org/data/2.5/weather?q=Kuala%20Lumpur&appid=YOUR_API_KEY"}',
                                    "name": "requests_tool",
                                },
                                "type": "function",
                            }
                        ]
                    },
                    "type": "AIMessageChunk",
                    "name": None,
                    "id": None,
                    "example": False,
                }
            ],
            tool_call_id="call_ePbadmMIlKqtY43OA5Sq98WZ",
        ),
        {
            "cod": 401,
            "message": "Invalid API key. Please see https://openweathermap.org/faq#error401 for more info.",
        },
    ],
    [
        AgentActionMessageLog(
            tool="universal_search",
            tool_input={"query": "Kuala Lumpur weather"},
            log="\nInvoking: `universal_search` with `{'query': 'Kuala Lumpur weather'}`\n\n\n",
            type="AgentActionMessageLog",
            message_log=[
                {
                    "content": "",
                    "additional_kwargs": {
                        "tool_calls": [
                            {
                                "index": 0,
                                "id": "call_q7IoAdmd8XFKWyM1jArgp3y1",
                                "function": {
                                    "arguments": '{"query":"Kuala Lumpur weather"}',
                                    "name": "universal_search",
                                },
                                "type": "function",
                            }
                        ]
                    },
                    "type": "AIMessageChunk",
                    "name": None,
                    "id": None,
                    "example": False,
                }
            ],
            tool_call_id="call_q7IoAdmd8XFKWyM1jArgp3y1",
        ),
        "weather is good",
    ],
    [
        AgentActionMessageLog(
            tool="calculator",
            tool_input={"query": 1},
            log="\nInvoking: `calculator` with `{'query': 1}`\n\n\n",
            type="AgentActionMessageLog",
            message_log=[
                {
                    "content": "",
                    "additional_kwargs": {
                        "tool_calls": [
                            {
                                "index": 0,
                                "id": "call_q7IoAdmd8XFKWyM1jArgp3y1",
                                "function": {
                                    "arguments": '{"query": 1}',
                                    "name": "calculator",
                                },
                                "type": "function",
                            }
                        ]
                    },
                    "type": "AIMessageChunk",
                    "name": None,
                    "id": None,
                    "example": False,
                }
            ],
            tool_call_id="call_q7IoAdmd8XFKWyM1jArgp3y1",
        ),
        10,
    ],
]


def test_get_zion_agent_actions() -> None:
    output = get_zion_agent_actions(langchain_intermediate_steps)
    assert len(output) == 3  # noqa: PLR2004

    # Support multiple types of tool_output
    assert isinstance(output[0].tool_output, dict)
    assert isinstance(output[1].tool_output, str)
    assert isinstance(output[2].tool_output, int)


def test_mask_inputs() -> None:
    inputs = {
        "input": "random input",
        "system_prompt": "You are a helpful agent...",
        "chat_history": [HumanMessage(content="1+1=?"), AIMessage(content="2")],
        "system_prompt_variables": {
            "name": "John",
            "age": "30",
        },
        "structured_response_schema": {
            "able_to_answer": {
                "description": "Whether able to provide answer to the user message.",
                "value_type": "bool",
            }
        },
        "intermediate_steps": [],
    }
    output = mask_inputs(inputs)

    assert output["input"] == f"{INFO_MASKED} (len: 12)"
    assert output["system_prompt"] == f"{INFO_MASKED} (len: 26)"
    assert output["chat_history"] == [HumanMessage(content=f"{INFO_MASKED} (len: 143)")]
    assert output["system_prompt_variables"] == f"{INFO_MASKED} (len: 29)"
    assert output["structured_response_schema"] == f"{INFO_MASKED} (len: 112)"
    assert output["intermediate_steps"] == f"{INFO_MASKED} (len: 2)"

    # Avoid NoneType throwing error
    assert mask_inputs(None) == {}


def test_mask_outputs() -> None:
    outputs = {
        "output": "random output",
        "structured_response": {
            "able_to_answer": True,
        },
    }
    output = mask_outputs(outputs)

    assert output["output"] == f"{INFO_MASKED} (len: 13)"
    assert output["structured_response"] == f"{INFO_MASKED} (len: 24)"

    # Avoid NoneType throwing error
    assert mask_outputs(None) == {}


def test_mask_any_value() -> None:
    assert mask_any_value("random input") == f"{INFO_MASKED} (len: 12)"
    assert mask_any_value(123) == f"{INFO_MASKED} (len: 3)"
    assert mask_any_value(None) is None
    assert mask_any_value(value=True) == f"{INFO_MASKED} (len: 4)"
    assert mask_any_value({}) == f"{INFO_MASKED} (len: 2)"
    assert mask_any_value(["str", 2]) == f"{INFO_MASKED} (len: 10)"
