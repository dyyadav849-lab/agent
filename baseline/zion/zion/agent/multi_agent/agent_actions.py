from langchain_core.messages import BaseMessage, ToolCall

from zion.tool.agent_tool import ZionAgentActions


def extract_agent_actions_from_messages(
    messages: list[BaseMessage],
) -> list[ZionAgentActions]:
    agent_actions: list[ZionAgentActions] = []

    for i in range(len(messages)):
        # check if message is AI/HumanMessage that contains tool_calls (ToolMessage does not contain tool_calls)
        if messages[i].type != "tool" and messages[i].tool_calls:
            tool_calls: list[ToolCall] = messages[i].tool_calls
            agent_actions.extend(
                ZionAgentActions(
                    tool_call_id=call.get("id"),
                    tool=call.get("name"),
                    tool_input=call.get("args"),
                )
                for call in tool_calls
            )

        # assumes corresponding ToolMessage always exists for AIMessage with non-empty tool_calls, matched by tool_call_id and name
        if messages[i].type == "tool":
            for j in range(len(agent_actions)):
                if (
                    agent_actions[j].tool_call_id == messages[i].tool_call_id
                    and agent_actions[j].tool == messages[i].name
                ):
                    agent_actions[j].tool_output = messages[i].content

    return agent_actions
