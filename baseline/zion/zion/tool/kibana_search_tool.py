# ruff: noqa: PLR0913, TRY300, PLC0206, N806, PLR2004, S113, PLR0912, C901
import json
from datetime import datetime
from typing import Any, Optional
from urllib.parse import urlparse

import requests
from langchain.callbacks.manager import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain.tools import BaseTool
from langchain_core.tools import ToolException
from pandas import Timestamp
from pydantic import BaseModel, Field
from requests.auth import HTTPBasicAuth

from zion.config import global_config, logger
from zion.tool import constant
from zion.tool.models.kibana_search_tool_model import (
    KibanaLogRecord,
    KibanaLogRecordAggregated,
)


class KibanaLogSearchInput(BaseModel):
    index: str = Field(description="name of index, default is k8s* if not specified")
    app_name: str = Field(description="name of app which is associated to service name")
    message: str = Field(description="keyword to search in log")
    date_from: datetime | str = Field(
        description="limit search to find logs from start date."
    )
    date_to: datetime | str = Field(
        description="limit search to find logs before end date."
    )
    filters: str = Field(
        default="",
        description=(
            "It is for other filter conditions that is not index, app_name, message, date_from, date_to."
            "example, you can pass in app_instance, log_level in the form below"
            "an array, every object inside represents list of dictionaries where each dictionary has two fields:"
            "- 'name': the key we are filtering by"
            "- 'query': the corresponding value for that key"
            "pass in empty string if nothing is needed to be filtered, ''"
        ),
    )


class KibanaLogSearch(BaseTool):
    name: str = "kibana_log_search"
    description: str = """
    Searches Kibana cluster.

    # Kibana Log Search Time Range Expressions for date_from and date_to

    Examples:
    # Last 5 Minutes:
    date_from = "now/m-5m" AND date_to = "now"

    # Last Hour:
    date_from =  "now/h-1h" AND date_to = "now"

    # Last Day:
    date_from =  "now/d-1d" AND date_to = "now"

    # Last Week:
    date_from =  "now/w-1w" AND date_to = "now"

    Returns:
    list[str]: The list of logs

    Raises:
        DependencyError

    Example:
    >> search("k8s*", "zion", "ERROR", datetime.utcnow() - timedelta(minutes=10), datetime.utcnow())
    >> search("grab", "ti-support-bot", "", "now/d-1d", "now")
    >> search("index1", "service-1", "hello", "now/d-5d", "now/d-1d")
    >> search("index2", "service-2", "", "now/m-5m", "now")
    >> search("index3", "service-3", "ERROR", "now/h-5h", "now")
    ["log a", "log b", "log c"]
    """
    args_schema: type[BaseModel] = KibanaLogSearchInput
    handle_tool_error: bool = True  # handle ToolExceptions
    metadata: Optional[dict[str, Any]] = None

    def __init__(self) -> None:
        super().__init__()

    def _generate_request_body(
        self,
        index: str,
        app_name: str,
        message: str,
        date_from: datetime | str,
        date_to: datetime | str,
        filters: str = "",
    ) -> Optional[dict[str, Any]]:
        filter_data = []
        if filters != "":
            filter_data = json.loads(filters)

        filters_match_phrases = [
            {"match_phrase": {filter_["name"]: str(filter_["query"])}}
            for filter_ in filter_data
        ]

        if isinstance(date_from, datetime):
            date_from_string = date_from.isoformat(timespec="milliseconds")
        else:
            date_from_string = date_from

        if isinstance(date_to, datetime):
            date_to_string = date_to.isoformat(timespec="milliseconds")
        else:
            date_to_string = date_to

        must_match = []
        size = 20

        if self.metadata is not None:
            for key in self.metadata:
                if self.metadata.get(key, None) is not None:
                    if key == "index":
                        index = self.metadata.get(key)
                    elif key == "app_name":
                        app_name = self.metadata.get(key)
                    elif key == "size":
                        size = self.metadata.get(key)
                    elif key == "gte":
                        date_from_string = self.metadata.get(key)
                    elif key == "lte":
                        date_to_string = self.metadata.get(key)
                    elif key == "must":
                        for must_key in self.metadata[key]:
                            match_condition = {}
                            match_condition[must_key] = self.metadata[key].get(must_key)
                            must_match.append({"match_phrase": match_condition})

        if message:
            must_match.append({"match_phrase": {"message": message}})

        query = {
            "size": size,
            "sort": [{"@timestamp": {"order": "desc", "unmapped_type": "boolean"}}],
            "query": {
                "bool": {
                    "must": [],
                    "filter": [
                        *filters_match_phrases,
                        *must_match,
                        {
                            "match_phrase": {
                                "app_name": app_name,
                            },
                        },
                        {
                            "range": {
                                "@timestamp": {
                                    "gte": date_from_string,
                                    "lte": date_to_string,
                                }
                            }
                        },
                    ],
                    "should": [],
                    "must_not": [],
                }
            },
        }

        return {"params": {"index": index, "body": query}}

    def _search_with_kibana(
        self, request_body: Optional[dict[str, Any]], index: str = "k8s*"
    ) -> list[str]:
        try:
            auth = HTTPBasicAuth(
                global_config.kibana_username, global_config.kibana_password
            )
            result = requests.post(
                global_config.kibana_base_url,
                headers={"Content-Type": "application/json"},
                json=request_body,
                auth=auth,
            )

            # Check if the response is successful
            records: list[KibanaLogRecord] = []
            current: dict[str, KibanaLogRecordAggregated] = {}

            if result.status_code == 200:
                # Parse the JSON response content
                response = result.json()
                # Check if "hits" is in the response
                if "rawResponse" in response and "hits" in response["rawResponse"]:
                    responseHits = response["rawResponse"]["hits"]
                    if "hits" in responseHits:
                        for hit in responseHits["hits"]:
                            self.extract_and_build_search_response_aggregated(
                                current=current,
                                base_url=self.get_kibana_base_url_from_opensearch(
                                    global_config.kibana_base_url
                                ),
                                index=self.get_opensearch_index_url(index),
                                response=hit,
                                skip_truncate=False,
                            )

                for x in current:
                    records.append(current[x].__repr__())  # noqa: PERF401

                return records
            logger.error(
                f"Request failed with status code {result.status_code} and response: {result.text}"
            )
            return []

        except Exception as e:
            raise ToolException(str(e)) from e

    def _run(
        self,
        app_name: str,
        message: str,
        date_from: datetime | str = "now/d-2d",
        date_to: datetime | str = "now",
        index: str = "k8s*",
        filters: str = "",
        _: Optional[CallbackManagerForToolRun] = None,
    ) -> list[str]:
        request_body = self._generate_request_body(
            index, app_name, message, date_from, date_to, filters
        )
        return self._search_with_kibana(request_body, index)

    async def _arun(
        self,
        app_name: str,
        message: str,
        date_from: datetime | str = "now/d-2d",
        date_to: datetime | str = "now",
        index: str = "k8s*",
        filters: str = "",
        _: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> list[str]:
        request_body = self._generate_request_body(
            index, app_name, message, date_from, date_to, filters
        )
        return self._search_with_kibana(request_body, index)

    def get_opensearch_index_url(self, index: str) -> str:
        if index == "grab-*":
            return "grab"

        if index == "k8s*":
            return "k8s"

        return index

    def get_kibana_base_url_from_opensearch(self, url: str) -> str:
        parsed_url = urlparse(url)
        return constant.OPENSEARCH_TO_KIBANA_URL[parsed_url.netloc]

    def truncate_log(self, content: str, max_len: int) -> str:
        if len(content) <= max_len:
            return content

        return f"{content[0:max_len]}{constant.TRUNCATED_TAG}"

    def truncate_field(
        self, source: dict, field: str, *, skip_truncate: bool, max_len: int
    ) -> str:
        if field not in source:
            return ""

        if skip_truncate:
            return source[field]
        return self.truncate_log(source[field], max_len)

    def extract_and_build_search_response_aggregated(
        self,
        current: dict[str, KibanaLogRecordAggregated],
        base_url: str,
        index: str,
        response: dict[str, str],
        *,
        skip_truncate: bool = False,
    ) -> dict[str, KibanaLogRecordAggregated]:
        source = response["_source"]
        msg = source["message"]

        # Some log put all content in request or response, bedide from message, we need to append log from those 2 fields as well.
        common_request = self.truncate_field(
            source=source,
            field="common_request",
            skip_truncate=skip_truncate,
            max_len=constant.MAX_LEN_LOG,
        )
        common_response = self.truncate_field(
            source=source,
            field="common_response",
            skip_truncate=skip_truncate,
            max_len=constant.MAX_LEN_LOG,
        )
        common_request_id = self.truncate_field(
            source=source,
            field="common_request_id",
            skip_truncate=skip_truncate,
            max_len=constant.MAX_LEN_LOG,
        )
        common_error = self.truncate_field(
            source=source,
            field="common_error",
            skip_truncate=skip_truncate,
            max_len=constant.MAX_LEN_LOG,
        )
        additional_data = self.truncate_field(
            source=source,
            field="additional_data",
            skip_truncate=skip_truncate,
            max_len=constant.MAX_ADDITIONAL_DATA_LEN_MSG,
        )
        stacktrace = self.truncate_field(
            source=source,
            field="stacktrace",
            skip_truncate=skip_truncate,
            max_len=constant.MAX_STACKTRACE_LEN_MSG,
        )
        msg = self.truncate_field(
            source=source,
            field="message",
            skip_truncate=skip_truncate,
            max_len=constant.MAX_STACKTRACE_LEN_MSG,
        )

        timestamp = self.truncate_field(
            source=source,
            field="@timestamp",
            skip_truncate=skip_truncate,
            max_len=constant.MAX_STACKTRACE_LEN_MSG,
        )

        rounded_timestamp = self.round_nearest_minute(timestamp, 5)

        final_msg = constant.LINE_BREAK_DELIMITER.join(
            self.build_non_empty_string_array(
                stacktrace,
                additional_data,
                common_error,
                msg,
                common_request,
                common_response,
            ),
        )

        key = f"{final_msg}:{rounded_timestamp}"

        if not skip_truncate:
            final_msg = self.truncate_log(final_msg, constant.MAX_KIBANA_LEN_MSG)

        if final_msg not in current:
            current[key] = KibanaLogRecordAggregated(
                url=constant.KIBANA_SINGLE_DOC_URL_FORMAT
                % (base_url, index, response["_index"], response["_id"]),
                message=final_msg,
                occurences=1,
                request_ids=[common_request_id],
            )
        else:
            # only fetch top 3 occurences
            if current[key].occurences < constant.MAX_REQUEST_ID_SAMPLE:
                current[key].request_ids.append(common_request_id)
            current[key].occurences = current[key].occurences + 1

        return current

    def round_nearest_minute(self, time: str, minutes: int) -> str:
        return (
            Timestamp.fromisoformat(time)
            .round(f"{minutes}min", ambiguous="raise", nonexistent="raise")
            .isoformat()
        )

    def build_non_empty_string_array(self, *args: str) -> list[str]:
        return [arg for arg in args if arg != ""]
