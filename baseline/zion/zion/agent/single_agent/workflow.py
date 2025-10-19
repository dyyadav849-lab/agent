from langgraph.graph import END, StateGraph
from langgraph.pregel import Pregel

from zion.agent.model import ChatGrabGPT
from zion.agent.single_agent.single_agent import (
    SingleAgentPrompts,
    SingleAgentState,
    SingleAgentStructuredRespDescriptions,
    create_single_agent_node,
)


def get_single_agent_system(
    tools: list,
    model: ChatGrabGPT,
    prompts: SingleAgentPrompts,
    descriptions: SingleAgentStructuredRespDescriptions,
) -> Pregel:
    workflow = StateGraph(SingleAgentState)

    workflow.add_node(
        "single_agent",
        create_single_agent_node(
            model,
            prompts.single_agent_prompt,
            tools,
            descriptions,
        ),
    )
    workflow.set_entry_point("single_agent")
    workflow.add_edge("single_agent", END)

    return workflow.compile()
