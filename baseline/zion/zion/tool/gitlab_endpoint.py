import base64
import time
from typing import Any, Optional
from urllib.parse import quote

import requests
from langchain.tools import BaseTool
from langchain_core.tools import ToolException
from pydantic import BaseModel, Field

from zion.config import global_config, logger, statsd
from zion.stats.datadog import DatadogClient
from zion.tool.sourcegraph import get_proto_file_path_by_service_name


class GitlabEndpointToolInput(BaseModel):
    service_name: str = Field(
        description="the service name to get service information."
    )


class GitlabEndpointTool(BaseTool):
    name: str = "gitlab_endpoint"
    description: str = """
    Used to answer any question related to service endpoint.
    """
    args_schema: type[BaseModel] = GitlabEndpointToolInput
    handle_tool_error: bool = True
    metadata: Optional[dict[str, Any]] = None

    def _run(self, service_name: str) -> str:
        """Use the tool."""

        return self.fetch_list_endpoints(service_name)

    async def _arun(self, service_name: str) -> str:
        """Use the tool asynchronously."""

        return self.fetch_list_endpoints(service_name)

    def get_gitlab_file_content(self, project_id: str, file_path: str) -> str:
        """Get file content from Gitlab by project id and file path."""

        # Before triggering external request
        start_time = time.perf_counter()
        log_tags = {
            "event_type": "external",
        }
        stat_tags = ["service:gitlab", "endpoint:get_file_content"]

        encoded_file_path = quote(file_path, safe="")
        url = f"https://gitlab.myteksi.net/api/v4/projects/{project_id}/repository/files/{encoded_file_path}?ref=master"
        # Example: https://gitlab.myteksi.net/api/v4/projects/17/repository/files/food%2Ffood-cart%2Fpb%2Foffers.proto?ref=master
        response = requests.get(
            url, headers={"PRIVATE-TOKEN": global_config.gitlab_api_token}, timeout=120
        )

        # Tracking when request completes
        elapsed_time = time.perf_counter() - start_time
        statsd.track_elapsed(
            metric=DatadogClient.METRIC_EXTERNAL, value=elapsed_time, tags=stat_tags
        )

        if response.status_code == requests.codes.not_found:
            # The request got error
            statsd.track_error(
                metric=DatadogClient.METRIC_EXTERNAL, error="not_found", tags=stat_tags
            )
            return "No gitlab file found. Please check the file path and try again."
        if response.status_code != requests.codes.ok:
            # The request got error
            statsd.track_error(
                metric=DatadogClient.METRIC_EXTERNAL,
                error=f"err_{response.status_code}",
                tags=stat_tags,
            )
            logger.error(
                f"Failed to get file content for the file path: {file_path}",
                tags=dict(log_tags, common_error=response.text),
            )
            return f"Failed to get file content for the file path: {file_path}"

        # The request got success
        statsd.track_success(metric=DatadogClient.METRIC_EXTERNAL, tags=stat_tags)

        file_content = response.json()["content"]
        return base64.b64decode(file_content).decode("utf-8")

    def fetch_list_endpoints(self, service_name: str) -> dict:
        """Used to answer any question related to service endpoint."""

        proto_by_service = {}
        monorepo_project_id = "17"
        proto_item = []
        try:
            protos = get_proto_file_path_by_service_name(service_name)

            for proto in protos:
                proto_name = proto["file"]["name"]
                proto_path = proto["file"]["path"]
                proto_content = self.get_gitlab_file_content(
                    monorepo_project_id, proto_path
                )
                proto_by_service[proto_name] = proto_content
                logger.debug(
                    f"Download proto file ={proto_name} done",
                    tags={"event_type": "tool.gitlab"},
                )

            for idx, (k, v) in enumerate(proto_by_service.items()):  # noqa: B007
                proto_item.append(v)

            return proto_item  # noqa: TRY300

        except Exception as e:
            err_message = f"Failed to download proto file for service {service_name}: got exception"
            logger.error(
                err_message, tags={"event_type": "tool.gitlab", "common_error": e}
            )
            raise ToolException(err_message) from e
