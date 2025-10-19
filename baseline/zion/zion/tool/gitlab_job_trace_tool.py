import json
from typing import Optional

from langchain.callbacks.manager import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain.tools import BaseTool
from langchain_core.documents import Document
from langchain_core.tools import ToolException
from pydantic import BaseModel, Field

from zion.util.constant import DocumentTitle, DocumentUri
from zion.util.gitlab import get_job_trace, parse_gitlab_job_url


class GitlabJobTraceInput(BaseModel):
    gitlab_url: str = Field(
        description="the gitlab job url to get more job trace metadata from gitlab. An example gitlab job url is such as: https://gitlab.myteksi.net/techops-automation/ti-support-bot/-/jobs/67291682"
    )


class GitlabJobTraceTool(BaseTool):
    name: str = "gitlab_job_trace"
    description: str = "Used to get job trace metadata for gitlab job links attached by user in their messages"
    args_schema: type[BaseModel] = GitlabJobTraceInput
    handle_tool_error: bool = True  # handle ToolExceptions

    def gitlab_job_trace_tool(self, gitlab_url: str) -> str:
        """Used to get job trace metadata for gitlab job links"""
        job_trace: str
        num_lines_of_trace: int = 200

        try:
            project_name, job_id = parse_gitlab_job_url(gitlab_url)

            job_trace = get_job_trace(
                project_name=project_name,
                job_id=job_id,
                num_lines=num_lines_of_trace,
            )
        except ValueError as e:
            raise ToolException(str(e)) from e

        return json.dumps(
            [
                Document(
                    page_content=job_trace,
                    metadata={
                        DocumentTitle: gitlab_url,
                        DocumentUri: gitlab_url,
                    },
                ).__dict__
            ]
        )

    def _run(
        self, gitlab_url: str, _: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Used to get job trace metadata for gitlab job links attached by user in their messages"""
        return self.gitlab_job_trace_tool(gitlab_url)

    async def _arun(
        self, gitlab_url: str, _: Optional[AsyncCallbackManagerForToolRun] = None
    ) -> str:
        """Used to get job trace metadata for gitlab job links attached by user in their messages"""
        return self.gitlab_job_trace_tool(gitlab_url)
