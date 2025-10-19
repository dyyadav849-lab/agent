from __future__ import annotations

import json
from typing import Any, Optional

import requests
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from zion.data.agent_plugin.http_plugin import decrypt_base_headers_secret_value
from zion.openapi.openapi_plugin import BaseHeaderConfig


class RequestsToolInput(BaseModel):
    http_method: str = Field(
        description="HTTP method of request, for example 'GET'", default=""
    )
    http_full_url_with_query: str = Field(
        description="Full URL of HTTP request, together with query", default=""
    )
    http_body: str = Field(
        description="Body of HTTP request. Can be an empty string('')", default=""
    )
    http_headers: str = Field(
        description="Headers of HTTP request. Can be an empty string('')", default=""
    )


class RequestsTool(BaseTool):
    name: str = "requests_tool"
    description: str = """
        Use this to make an HTTP request. The input of this tool is based on open api specification.
        If the URL path contains route parameters, replace the value in curly braces instead of adding them as query parameters.
        If the query parameters are needed, add them in URL path according to standard URL format.
        Please ensure the http_headers parameter is provided as a string in the JSON format, for example: "{"Content-Type": "application/json"}".
        Note: The http_headers parameter can also be an empty string ("").
        """
    args_schema: type[BaseModel] = RequestsToolInput
    handle_tool_error: bool = True
    metadata: Optional[dict[str, Any]] = None

    def _run(
        self,
        http_method: str,
        http_full_url_with_query: str,
        http_headers: str = "",
        http_body: str = "",
    ) -> str:
        """Use the tool."""

        return self.http_request(
            http_method, http_full_url_with_query, http_headers, http_body
        )

    async def _arun(
        self,
        http_method: str,
        http_full_url_with_query: str,
        http_headers: str = "",
        http_body: str = "",
    ) -> str:
        """Use the tool asynchronously."""

        return self.http_request(
            http_method, http_full_url_with_query, http_headers, http_body
        )

    def http_request(
        self,
        http_method: str,
        http_full_url_with_query: str,
        http_headers: str = "",
        http_body: str = "",
    ) -> str:
        res_body_text = ""

        try:
            headers = json.loads(http_headers) if http_headers != "" else {}

            header_config = [
                BaseHeaderConfig(name=key, value=value)
                for key, value in headers.items()
            ]
            decrypt_base_headers_secret_value(header_config)
            headers = {
                decrypted_header.name: decrypted_header.value
                for decrypted_header in header_config
            }

            if http_method.lower() == "get":
                res = requests.get(
                    url=http_full_url_with_query, headers=headers, timeout=90
                )
                res_body_text = res.json()
            elif http_method.lower() == "post":
                body = json.loads(http_body) if http_body != "" else {}
                res = requests.post(
                    url=http_full_url_with_query,
                    headers=headers,
                    json=body,
                    timeout=90,
                )
                res_body_text = res.json()
            elif http_method.lower() == "put":
                body = json.loads(http_body) if http_body != "" else {}
                res = requests.put(
                    url=http_full_url_with_query,
                    headers=headers,
                    json=body,
                    timeout=90,
                )
                res_body_text = res.json()

        except requests.exceptions.RequestException as e:
            res_body_text = str(e)
        except ValueError as valueErr:
            res_body_text = str(valueErr)

        return res_body_text
