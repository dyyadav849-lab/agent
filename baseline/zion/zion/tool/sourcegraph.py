import time

import requests
from langchain_core.tools import tool

from zion.config import global_config, logger, statsd
from zion.stats.datadog import DatadogClient

sourcegraph_query = """query ($query: String!) {
    search(query: $query) {
        results {
            results { ... on FileMatch {
                    file { name path repository { name } }
                }
            }
            limitHit
            matchCount
            elapsedMilliseconds
        }
    }
}"""


@tool
def get_proto_file_path_by_service_name(service_name: str) -> dict:
    """Get Proto file of a service from Sourcegraph by service name."""

    # Before triggering external request
    start_time = time.perf_counter()
    log_tags = {
        "event_type": "external",
    }
    stat_tags = ["service:sourcegraph", "endpoint:search", "tool:search_proto"]

    url = f"{global_config.sourcegraph_host}/.api/graphql"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "token " + global_config.sourcegraph_access_token,
    }

    sourcegraph_query_variables = f"context:global repo:^{global_config.sourcegraph_query_gitlab_host}/gophers/go$ path:/{service_name}/pb/* file:\\.proto$"
    req_body = {
        "query": sourcegraph_query,
        "variables": {"query": sourcegraph_query_variables},
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=req_body,
            timeout=30,
            verify=global_config.sourcegraph_verify_certificate,
        )

        # Tracking when request completes
        elapsed_time = time.perf_counter() - start_time
        statsd.track_elapsed(
            metric=DatadogClient.METRIC_EXTERNAL, value=elapsed_time, tags=stat_tags
        )
        logger.debug(
            f"DEBUG: getting proto file. Received: Status code {response.status_code}; Response: {response.text}",
            tags=log_tags,
        )

        # Check response result
        if response.status_code == requests.codes.ok:
            data = response.json()
            match_count = data["data"]["search"]["results"]["matchCount"]
            if match_count == 0:
                statsd.track_error(
                    metric=DatadogClient.METRIC_EXTERNAL,
                    error="not_found",
                    tags=stat_tags,
                )
                return {
                    "error": "No proto file found. Sorry, at the moment, we just support services in Go Monorepo"
                }

            statsd.track_success(metric=DatadogClient.METRIC_EXTERNAL, tags=stat_tags)
            return data["data"]["search"]["results"]["results"]

        # The request got error
        statsd.track_error(
            metric=DatadogClient.METRIC_EXTERNAL,
            error=f"err_{response.status_code}",
            tags=stat_tags,
        )
        logger.error(
            f"Failed to get proto file for service {service_name}. Received: Status code {response.status_code}",
            tags=dict(log_tags, common_error=response.text),
        )
        return {"error": f"Error getting proto file: {response.text}"}  # noqa: TRY300, TODO(Huong): this is not runtime error, just a coding recommendation. Might find a way to fix this warning.

    except Exception as e:  # noqa: BLE001
        statsd.track_error(
            metric=DatadogClient.METRIC_EXTERNAL, error="exception", tags=stat_tags
        )
        logger.error(
            f"Failed to get proto file for service {service_name}: got exception",
            tags=dict(log_tags, common_error=e),
        )
        return {"error": f"Error getting proto file. Exception: {e}"}
