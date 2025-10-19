from __future__ import annotations

import json
from typing import Any, Optional

import requests
from langchain.callbacks.manager import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain.tools import BaseTool
from langchain_core.tools import ToolException
from pydantic import BaseModel, Field

from zion.config import global_config, logger

HTTP_OK_STATUS = "OK"

GLEAN_RESULT_SIZE = 100


class ShortcutsInput(BaseModel):
    query: str = Field(description="shortcuts query to get list of shortcuts")


class GleanListshortcutsTool(BaseTool):
    name: str = "glean_listshortcuts"
    description: str = (
        "List shortcuts editable/owned by the currently authenticated user."
    )
    args_schema: type[BaseModel] = ShortcutsInput
    handle_tool_error: bool = True  # handle ToolExceptions
    metadata: Optional[dict[str, Any]] = None

    def _build_glean_request_body(self, query: str) -> dict:
        return {
            "query": query,
            "pageSize": GLEAN_RESULT_SIZE,
        }

    def glean_res(self, result_item: any, go_link: str) -> str:
        destination_url = ""
        alias_name = go_link.replace("go/", "")
        alias_name = alias_name.translate(
            str.maketrans("", "", ".:@&~-_")
        )  ## GO Link Only support ., :, @, &, ~, -, and _

        if "shortcuts" not in result_item:
            return destination_url

        result = result_item.get("shortcuts", [])
        for single_document_item in result:
            if single_document_item["alias"] == alias_name:
                destination_url = single_document_item.get("destinationUrl", "")
                break

        return destination_url

    def glean_listshortcuts_tool(self, query: str) -> str:
        """Used to retrieve list of shortcuts for the given typed query from Glean"""

        req_body = self._build_glean_request_body(query)

        res = requests.post(
            url=f"{global_config.glean_base_url}/rest/api/v1/listshortcuts",
            data=json.dumps(req_body),
            headers={"Authorization": f"Bearer {global_config.glean_bearer_token}"},
            timeout=20,
        )
        if res.reason != HTTP_OK_STATUS:
            err_msg = f"Glean shortcuts failed with status code `{res.status_code}` and reason `{res.reason}`, response: {res.text}"
            logger.error(err_msg)
            raise ToolException(err_msg)

        return json.dumps(self.glean_res(res.json(), query))

    def _run(self, query: str, _: Optional[CallbackManagerForToolRun] = None) -> str:
        """Retrieve list of shortcuts for the given typed query"""
        return self.glean_listshortcuts_tool(query)

    async def _arun(
        self, query: str, _: Optional[AsyncCallbackManagerForToolRun] = None
    ) -> str:
        """Retrieve list of shortcuts for the given typed query asynchronously"""
        return self.glean_listshortcuts_tool(query)
