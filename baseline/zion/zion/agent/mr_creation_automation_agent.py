import json

from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
)
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

from zion.agent.model import ChatGrabGPT
from zion.config import global_config
from zion.tool.constant import mr_creation_search_tool_desc
from zion.tool.glean_search import GleanSearchTool


class MCPMrCreationAutomationAgentState(BaseModel):
    messages: str = Field(description="A success message describing the result.")
    mr_link: str = Field(description="The link to the created merge request.")


async def create_mr_creation_automation_agent_node(
    model: ChatGrabGPT,
    prompt: str,
    query_source: dict,
    query: str,
    chat_history: list[str],
) -> MCPMrCreationAutomationAgentState:
    config = {
        "mcp-gitlab-mr-creation-template": {
            "url": global_config.mcp_gitlab_mr_creation_template + "/mcp/",
            "transport": "streamable_http",
        }
    }
    mcp_client = MultiServerMCPClient(config)
    tools = await mcp_client.get_tools()  # config URL MUST end with "/" to ensure the client does not enter streaming mode but correctly fetches the tools.

    # append glean search tool to access the url provided by user
    glean_search = GleanSearchTool(description=mr_creation_search_tool_desc)
    tools.append(glean_search)

    # Create the agent with proper configuration
    react_agent = create_react_agent(
        model=model,
        tools=tools,
        response_format=MCPMrCreationAutomationAgentState,
        prompt=prompt,
    )

    chat_history_str = "\n".join(chat_history)

    # Create a system message with the access token and format instructions
    system_message = SystemMessage(
        content=f"""
        Access Token: {global_config.grab_gitlab_access_token} \nChannel Name: {query_source.channel_name.replace("#", "")} \nWorkflow Id: {query_source.workflow_id.replace("#", "")}  \n\n chat history: {chat_history_str}
        """
    )

    if chat_history:
        formatted_output = f"query: {query}\n\nchat_history:\n" + "\n".join(
            chat_history
        )
    else:
        formatted_output = f"query: {query}\nchat_history: None"

    # Prepare the input with proper structure
    input_data = {"messages": [system_message, HumanMessage(content=formatted_output)]}

    try:
        # Use the agent executor with proper error handling
        response = await react_agent.ainvoke(input_data)

        # Extract MR link safely
        mr_link = ""
        if (
            isinstance(response, dict)
            and "structured_response" in response
            and isinstance(
                response["structured_response"], MCPMrCreationAutomationAgentState
            )
        ):
            return response["structured_response"]

        # Extract the response content safely
        response_content = ""
        if isinstance(response, dict):
            if "output" in response:
                response_content = response["output"]
            elif response.get("messages"):
                response_content = (
                    response["messages"][-1].content
                    if response["messages"][-1].content
                    else ""
                )

        # Try to parse the response as JSON if it's a string
        if isinstance(response_content, str):
            try:
                parsed_response = json.loads(response_content)
                if isinstance(parsed_response, dict):
                    return MCPMrCreationAutomationAgentState(
                        messages=parsed_response.get("messages", ""),
                        mr_link=parsed_response.get("mr_link", ""),
                    )
            except json.JSONDecodeError:
                pass

        # Create the response in the correct format
        return MCPMrCreationAutomationAgentState(
            messages=response_content,
            mr_link=mr_link,
        )
    except Exception as e:  # noqa: BLE001
        # Handle any errors gracefully
        error_message = f"Error during agent execution: {e!s}"
        return MCPMrCreationAutomationAgentState(
            messages=error_message,
            mr_link="",
        )
