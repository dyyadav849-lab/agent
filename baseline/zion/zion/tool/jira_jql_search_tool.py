from typing import Optional

import yaml
from atlassian import Jira
from langchain.callbacks.manager import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain.tools import BaseTool
from langchain_core.tools import ToolException
from pydantic import BaseModel, Field
from requests.exceptions import HTTPError

from zion.config import global_config


class JiraJQLSearchInput(BaseModel):
    jql: str = Field(
        description="The JQL query to search JIRA issues. For example, `project = LLM`"
    )

    start: int = Field(description="The index of the first issue to return. (0-based)")

    limit: int = Field(description="The maximum number of issues to return.")


class JiraJQLSearch(BaseTool):
    name: str = "jira_jql_search"
    description: str = """
    This tool is a wrapper around atlassian-python-api's Jira jql API, useful when you need to search for Jira issues.

    For example, to find all the issues in project "Test" assigned to the me, you would pass in the following string:
    project = Test AND assignee = currentUser()
    or to find issues with summaries that contain the word "test", you would pass in the following string:
    summary ~ 'test'

    Some notable custom field in the Grab Jira
    - Tech Family: Represent the department name
    - Problem Space TF: Represent the problem space name
    - Severity: Represent the severity of the issue

    Note: When the custom field name has space, wrap them with double quotes. For example, "Tech Family".
    """
    args_schema: type[BaseModel] = JiraJQLSearchInput
    handle_tool_error: bool = True  # handle ToolExceptions
    jira: Jira | None = None

    def __init__(self) -> None:
        super().__init__()
        self.jira = Jira(
            url=global_config.jira_base_url,
            username=global_config.jira_username,
            password=global_config.jira_password,
            cloud=True,
        )

    def _search_with_jql(self, jql: str, start: int, limit: int) -> str:
        fields = [
            "summary",
            "description",
            "status",
            "assignee",
            "reporter",
            "created",
            "updated",
            "duedate",
            "labels",
            "components",
            "fixVersions",
            "priority",
            "severity",
        ]
        try:
            results = self.jira.jql(jql, fields=fields, start=start, limit=limit)
        except HTTPError as e:
            raise ToolException(str(e)) from e

        reduced_results = self._reduce_jql_results(results)

        result_with_jql_link = {
            "jira_search_result": reduced_results,
            "link_to_jira_results": f"{global_config.jira_base_url}/issues/?jql={jql}",
        }

        # Convert results to YAML str to save token
        return yaml.dump(result_with_jql_link, indent=4)

    def _reduce_jql_results(self, results: dict[str, any]) -> dict[str, any]:
        """Just keep the necessary properties in the Jira issue to reduce the size of the response"""

        if "issues" not in results:
            return results

        for issue in results["issues"]:
            # Remove unnecessary property in issue
            issue.pop("self", None)
            issue.pop("expand", None)

            # Remove unnecessary properties in issue
            fields = issue.get("fields", {})
            if fields.get("reporter"):
                fields["reporter"] = {
                    "displayName": fields["reporter"]["displayName"],
                }

            if fields.get("assignee"):
                fields["assignee"] = {
                    "displayName": fields["assignee"]["displayName"],
                }

            if fields.get("components"):
                fields["components"] = [
                    {"name": comp["name"]} for comp in fields["components"]
                ]

            if fields.get("status"):
                fields["status"] = {"name": fields["status"]["name"]}

        return results

    def _run(
        self,
        jql: str,
        start: int = 0,
        limit: int = 10,
        _: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        return self._search_with_jql(jql, start, limit)

    async def _arun(
        self,
        jql: str,
        start: int = 0,
        limit: int = 10,
        _: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        return self._search_with_jql(jql, start, limit)
