import base64
import re
import time
from urllib.parse import quote

import requests
import yaml

from zion.config import global_config, logger, statsd
from zion.stats.datadog import DatadogClient
from zion.util.datadog.datadog_client import get_downstream_qps, get_upstream_qps


def get_service_mesh(
    service_name: str, env: str, upstream_depth: int = 1, downstream_depth: int = 1
) -> dict:
    """Get Service Mesh config which declares communication between Grab services, their upstreams, downstreams..."""

    log_tags = {
        "event_type": "tools.mesh",
    }

    # List upstreams and downstreams
    streams = download_upstreams_downstreams(service_name, env)
    result = {"env": streams.get("env"), "service": streams.get("service")}

    # Query service QPS
    upstream_qps, downstream_qps = {}, {}
    try:
        upstream_qps = get_upstream_qps(service_name, env)
        downstream_qps = get_downstream_qps(service_name, env)
        logger.info(
            "DEBUG: Queried Upstream QPS for service name `%s`. Received: %s",
            service_name,
            upstream_qps,
            tags=log_tags,
        )
        logger.info(
            "DEBUG: Queried Downstream QPS for service name `%s`. Received: %s",
            service_name,
            downstream_qps,
            tags=log_tags,
        )
    except Exception as e:  # noqa: BLE001
        logger.warn(
            "Failed to query QPS for service name `%s`. Received error: %s",
            service_name,
            e,
            tags=log_tags,
        )
        return {"result": result, "note": ""}

    if upstream_depth > 0:
        result["upstreams"] = streams.get("upstreams")
        if streams.get("upstreams") is not None and upstream_qps is not None:
            result["upstream_qps"] = {
                k: v for k, v in upstream_qps.items() if k in result["upstreams"]
            }
    if downstream_depth > 0:
        result["downstreams"] = streams.get("downstreams")
        if streams.get("downstreams") is not None and downstream_qps is not None:
            result["downstream_qps"] = {
                k: v for k, v in downstream_qps.items() if k in result["downstreams"]
            }

    more_info = f"""
    If you want to see the full list, please visit:
    • "{global_config.domain}/test/_get-dependency-graph?service_name=(service_name)" to see all the upstreams, downstreams of that service.
    To double check the QPS, please visit https://app.datadoghq.com/notebook/9121401/-service-insights-service-map-related-qps
    Reach out to @oncall-service-insights if you need more help.
    """
    return {
        "result": result,
        "note": f"Streams were ranked by their QPS in last 7 days. {more_info}",
    }


def download_mesh_config(
    service_name: str, env: str, *, outbound: bool = False
) -> dict:
    # Without asterisk (*) in the function def, got Ruff lint error FBT001: `Boolean-typed positional argument in function definition`.
    # In Python, it's generally considered a best practice to use keyword arguments for boolean parameters rather than positional arguments. This is because boolean flags can be easily confused or misinterpreted when passed as positional arguments.
    # -> It's recommended to add the asterisk (*) before the boolean parameter (this case, maybe we should keep the boolean parameters as the last ones).
    # The asterisk (*) in the function definition forces `outbound` to be a keyword-only argument, and providing a default value makes it optional.

    # Before triggering external request
    start_time = time.perf_counter()
    log_tags = {
        "event_type": "external",
    }
    stat_tags = [
        "service:gitlab",
        "endpoint:get_file_content",
        "tool:download_mesh_config",
    ]

    if outbound == 1:
        file_path = f"services/{service_name}/{env}/smi-outbound-config.yaml"
    else:
        file_path = f"services/{service_name}/{env}/smi-inbound-config.yaml"

    encoded_file_path = quote(file_path, safe="")
    url = f"https://gitlab.myteksi.net/api/v4/projects/15891/repository/files/{encoded_file_path}?ref=main"
    # Example: https://gitlab.myteksi.net/api/v4/projects/15891/repository/files/services%2Fabacus%2Fprd%2Fsmi-inbound-config.yaml?ref=main

    response = requests.get(
        url, headers={"PRIVATE-TOKEN": global_config.gitlab_api_token}, timeout=10
    )

    # Tracking when request completes
    elapsed_time = time.perf_counter() - start_time
    statsd.track_elapsed(
        metric=DatadogClient.METRIC_EXTERNAL, value=elapsed_time, tags=stat_tags
    )
    logger.info(
        f"DEBUG: download_mesh_config for service `{service_name}` with file name `{file_path}`, file url `{url}`. Received: Status code {response.status_code}; Response: {response.text}",
        tags=log_tags,
    )

    if response.status_code == requests.codes.not_found:
        # The request got error
        statsd.track_error(
            metric=DatadogClient.METRIC_EXTERNAL, error="not_found", tags=stat_tags
        )
        return {
            "error": "No proto file found. Sorry, at the moment, we just support services configured in Sentry Mesh Service Config repo."
        }
    if response.status_code != requests.codes.ok:
        # The request got error
        statsd.track_error(
            metric=DatadogClient.METRIC_EXTERNAL,
            error=f"err_{response.status_code}",
            tags=stat_tags,
        )
        logger.error(
            f"Failed to download proto file for service {service_name}",
            tags=dict(log_tags, common_error=response.text),
        )
        return {"error": f"Failed to get proto file for service {service_name}"}

    # The request got success
    statsd.track_success(metric=DatadogClient.METRIC_EXTERNAL, tags=stat_tags)

    file_content = response.json()["content"]
    file_content = base64.b64decode(file_content).decode("utf-8")

    return yaml.safe_load(file_content)


def download_upstreams_downstreams(service_name: str, env: str) -> dict:
    """Get upstreams and downstreams for a service."""

    log_tags = {
        "event_type": "tools.mesh",
    }
    downstreams = []
    inbound_resp = download_mesh_config(service_name, env, outbound=False)
    logger.info(
        f"DEBUG: download_upstreams_downstreams for service `{service_name}` in {env}. Received inbound Response: {inbound_resp}",
        tags=log_tags,
    )
    if inbound_resp.get("downstreams") is not None:
        for downstream in inbound_resp.get("downstreams"):
            s_name = re.sub("-outbound$", "", downstream)
            if s_name not in downstreams:
                downstreams.append(s_name)

    upstreams = []
    outbound_resp = download_mesh_config(service_name, env, outbound=True)
    logger.info(
        f"DEBUG: download_upstreams_downstreams for service `{service_name}` in {env}. Received outbound Response: {outbound_resp}",
        tags=log_tags,
    )
    if outbound_resp.get("upstreams") is not None:
        for s in outbound_resp.get("upstreams"):
            upstream_name = s.get("name")
            upstream_name = re.sub("-grpc$", "", upstream_name)
            upstream_name = re.sub("-http$", "", upstream_name)
            upstreams.append(upstream_name)

    return {
        "env": env,
        "service": service_name,
        "downstreams": downstreams,
        "upstreams": upstreams,
    }
