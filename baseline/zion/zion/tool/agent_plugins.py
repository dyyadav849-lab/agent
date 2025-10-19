from __future__ import annotations

from typing import Any, Literal

from langgraph.prebuilt import ToolNode
from pydantic import BaseModel

from zion.data.agent_plugin.util import get_agent_plugin_json
from zion.openapi.openapi_plugin import OpenAPIPlugin
from zion.tool.calculator_tool import calculator_tool
from zion.tool.concedo_role_extractor import ConcedoRoleExtractorTool
from zion.tool.document_kb_search_tool import HadesDocumentKBSearch
from zion.tool.download_mesh_inbound import DownloadMeshInboundTool
from zion.tool.ec2_log_retriever import Ec2LogRetriever
from zion.tool.get_document_content import GetDocumentContentTool
from zion.tool.get_service_dependencies import GetServiceDependenciesTool
from zion.tool.get_service_platform import GetServicePlatformTool
from zion.tool.gitlab_access_checker import GitlabRepositoryAccessCheckerTool
from zion.tool.gitlab_endpoint import GitlabEndpointTool
from zion.tool.gitlab_job_trace_tool import GitlabJobTraceTool
from zion.tool.gitlab_mr_creation_automation_tool import GitlabMrCreationAutomationTool
from zion.tool.glean_search import GleanSearchTool
from zion.tool.hades_kb_service import HadesKnowledgeBaseTool
from zion.tool.jira_jql_search_tool import JiraJQLSearch
from zion.tool.kibana_search_tool import KibanaLogSearch
from zion.tool.knowledge_base_search_tool import KnowledgeBaseSearchTool
from zion.tool.openai_web_search_tool import OpenaiWebSearchTool
from zion.tool.openapi_tool import OpenAPIPluginTool
from zion.tool.sleep_delay_tool import SleepDelayTool
from zion.tool.universal_search import UniversalSearchTool

COMMON_PLUGINS = {
    "calculator": calculator_tool,
    UniversalSearchTool().name: UniversalSearchTool,
    GleanSearchTool().name: GleanSearchTool,
    HadesDocumentKBSearch().name: HadesDocumentKBSearch,
    ConcedoRoleExtractorTool().name: ConcedoRoleExtractorTool,
    GitlabJobTraceTool().name: GitlabJobTraceTool,
    GitlabMrCreationAutomationTool().name: GitlabMrCreationAutomationTool,
    GetDocumentContentTool().name: GetDocumentContentTool,
    GitlabRepositoryAccessCheckerTool().name: GitlabRepositoryAccessCheckerTool,
    JiraJQLSearch().name: JiraJQLSearch,
    KnowledgeBaseSearchTool().name: KnowledgeBaseSearchTool,
    SleepDelayTool().name: SleepDelayTool,
    HadesKnowledgeBaseTool().name: HadesKnowledgeBaseTool,
    KibanaLogSearch().name: KibanaLogSearch,
    GetServiceDependenciesTool().name: GetServiceDependenciesTool,
    DownloadMeshInboundTool().name: DownloadMeshInboundTool,
    GitlabEndpointTool().name: GitlabEndpointTool,
    Ec2LogRetriever().name: Ec2LogRetriever,
    GetServicePlatformTool().name: GetServicePlatformTool,
    OpenaiWebSearchTool().name: OpenaiWebSearchTool,
}


class AgentPlugin(BaseModel):
    name: str
    type: Literal["openapi", "common", "http", "orchestrator"]
    # The metadata will be used to pass the configuration to the tool
    # It shouldn't used for passing sensitive information like API keys or any other secrets
    # since it will be traced by LangSmith
    metadata: dict[str, Any] | None = None


def get_tools_from_database_result(
    db_openapi_plugins: list[AgentPlugin],
) -> list[ToolNode]:
    """Converts the openapi plugin retrieved from database to a list of tool nodes"""
    tools: list[ToolNode] = []
    openapi_plugins = get_agent_plugin_json(db_openapi_plugins, open_api=True)
    for openapi_plugin in openapi_plugins:
        open_api_plugin = OpenAPIPlugin(**openapi_plugin)
        tools.append(OpenAPIPluginTool.from_plugin(plugin=open_api_plugin))

    return tools
