

from langgraph.graph import END, StateGraph
from langgraph.pregel import Pregel

from zion.agent.model import ChatGrabGPT
from zion.agent.multi_agent.able_to_answer_agent import (
    create_able_to_answer_agent_node,
    should_end,
)
from zion.agent.multi_agent.classes import (
    AgentState,
    MultiAgentPrompts,
    MultiAgentStructuredRespDescriptions,
)
from zion.agent.multi_agent.internal_search_agent import (
    create_internal_search_agent_node,
)
from zion.agent.multi_agent.query_categorizer_agent import (
    create_query_categorizer_agent_node,
    is_slack_workflow_category_answerable,
)
from zion.agent.multi_agent.ti_bot_agent import create_ti_bot_agent_node
from zion.tool.glean_search import GleanSearchTool
from zion.tool.hades_kb_service import HadesKnowledgeBaseTool


def get_ti_bot_multi_agent_system(
    tools: list,
    model: ChatGrabGPT,
    prompts: MultiAgentPrompts,
    descriptions: MultiAgentStructuredRespDescriptions,
) -> Pregel:
    workflow = StateGraph(AgentState)

    workflow.add_node(
        "query_categorizer_agent",
        create_query_categorizer_agent_node(
            model,
            prompts["query_categorizer_agent_prompt"],
            descriptions,
        ),
    )

    workflow.add_conditional_edges(
        "query_categorizer_agent",
        is_slack_workflow_category_answerable,
        {
            True: "ti_bot_agent",
            False: END,
        },
    )
    workflow.add_node(
        "ti_bot_agent",
        create_ti_bot_agent_node(
            model,
            prompts["ti_bot_agent_prompt"],
            [
                tool
                for tool in tools
                if tool.name
                not in {GleanSearchTool().name, HadesKnowledgeBaseTool().name}
                # should include GitlabJobTraceTool, GitlabRepositoryAccessCheckerTool, KibanaLogSearch, JiraJQLSearch, GetDocumentContentTool
            ],
        ),
    )

    # after getting logs/data from tools, add more context by using internal search
    workflow.add_edge("ti_bot_agent", "internal_search_agent")

    workflow.add_node(
        "internal_search_agent",
        create_internal_search_agent_node(
            model,
            prompts["internal_search_agent_prompt"],
            [
                tool
                for tool in tools
                if tool.name in {GleanSearchTool().name, HadesKnowledgeBaseTool().name}
            ],
            descriptions,
        ),
    )

    workflow.add_edge("internal_search_agent", "able_to_answer_agent")

    workflow.add_node(
        "able_to_answer_agent",
        create_able_to_answer_agent_node(
            model, prompts["able_to_answer_agent_prompt"], descriptions
        ),
    )

    workflow.add_conditional_edges(
        "able_to_answer_agent", should_end, {True: END, False: "ti_bot_agent"}
    )

    workflow.add_edge("able_to_answer_agent", END)

    workflow.set_entry_point("query_categorizer_agent")

    return workflow.compile()
