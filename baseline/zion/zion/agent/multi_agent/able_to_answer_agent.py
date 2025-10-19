from typing import Callable

from langchain_core.messages import AIMessage
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

from zion.agent.model import ChatGrabGPT
from zion.agent.multi_agent.classes import (
    AgentState,
    MultiAgentStructuredRespDescriptions,
)


def create_able_to_answer_response(
    descriptions: MultiAgentStructuredRespDescriptions,
) -> BaseModel:
    class AbleToAnswerResponse(BaseModel):
        able_to_answer: bool = Field(
            description=descriptions["able_to_answer_description"]
        )
        answer_confidence_score: int = Field(
            description=descriptions["answer_confidence_score_description"]
        )
        # add more details on what each score means
        # could get llm to return suggestions to ti_bot_agent on how to improve answer

    return AbleToAnswerResponse


MAX_ITERATIONS = 1


# func to determine if the able_to_answer agent should go to __end__
# should end if able to answer and final answer_confidence_score > 1
def should_end(state: AgentState) -> bool:
    return (
        state["able_to_answer"]
        and len(state["answer_confidence_scores"]) >= 1
        and state["answer_confidence_scores"][-1] > 1
    ) or len(state["answer_confidence_scores"]) >= MAX_ITERATIONS


def create_able_to_answer_agent_node(
    model: ChatGrabGPT, prompt: str, descriptions: MultiAgentStructuredRespDescriptions
) -> Callable:
    able_to_answer_agent = create_react_agent(
        model=model,
        tools=[],
        response_format=create_able_to_answer_response(descriptions),
        prompt=prompt,
    )

    def able_to_answer_agent_node(state: AgentState) -> AgentState:
        response = able_to_answer_agent.invoke(state)

        response_content = ""
        if response["messages"][-1].content:  # check if content is not None
            response_content = response["messages"][-1].content
        return {
            "messages": [
                AIMessage(
                    content=response_content,
                    name="able_to_answer_agent",
                )
            ],
            "able_to_answer": response["structured_response"].able_to_answer,
            "answer_confidence_scores": [
                response["structured_response"].answer_confidence_score
            ],
        }

    return able_to_answer_agent_node
