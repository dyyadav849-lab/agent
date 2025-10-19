import re  # noqa: INP001
from typing import Any

from datadog import api, initialize
from datadog_api_client import ApiClient, Configuration
from datadog_api_client.v2.api.logs_api import LogsApi


class _Client:
    # Init a private Datadog Client with options as defined in datadog "initialize" function.
    def __init__(self, options: dict) -> None:
        self.configuration = Configuration(
            api_key={
                "apiKeyAuth": options["api_key"],
                "appKeyAuth": options["app_key"],
            }
        )

        initialize(**options)
        self.api_client = ApiClient(self.configuration)
        self.logs = LogsApi(self.api_client)
        self.metric = api.Metric
        self.event = api.Event

    def get_event(self, event_id: Any):  # noqa: ANN202, ANN401, TODO(Huong): Add return value and re-enable this lint.
        return self.event.get(event_id)

    def get_event_from_url(self, alert_url: str):  # noqa: ANN202, TODO(Huong): Add return value and re-enable this lint.
        match = re.search(r"event_id=(\d+)", alert_url)
        if not match:
            return "Invalid alert URL"
        event_id = match.group(1)
        return self.get_event(event_id)

    # Query methods ...
    def query_metric(self, query: str, start_time: float, end_time: float):  # noqa: ANN202, TODO(Huong): Add return value and re-enable this lint.
        return self.metric.query(start=start_time, end=end_time, query=query)

    # Tracking methods ...
    def send_metric(self, metric: str, value: int, tags: list[str], typ: str):  # noqa: ANN202, TODO(Huong): Add return value and re-enable this lint.
        return self.metric.send(metric=metric, points=value, tags=tags, type=typ)

    def track_count(self, metric: str, tags: list[str]):  # noqa: ANN202, TODO(Huong): Add return value and re-enable this lint.
        return self.send_metric(f"{metric}.count", 1, tags, "count")

    def track_count_n(self, metric: str, value: int, tags: list[str]):  # noqa: ANN202, TODO(Huong): Add return value and re-enable this lint.
        return self.send_metric(f"{metric}.count", value, tags, "count")

    def track_elapsed(self, metric: str, value: int, tags: list[str]):  # noqa: ANN202, TODO(Huong): Add return value and re-enable this lint.
        return self.send_metric(f"{metric}.elapsed", value, tags, "histogram")


class DatadogClient(_Client):
    """Datadog client with common tracking methods"""

    # Default metrics
    METRIC_SLACK = "slack"
    METRIC_AGENT = "agent"
    METRIC_EXTERNAL = "external"
    EVENT_EVALUATION = "evaluation"

    def __init__(self, options: dict, env: str, appname: str) -> None:
        super().__init__(options)
        self.env = env  # The common "env" tag value.
        self.appname = appname  # The common "appname" tag value.
        self.prefix = "pystatsd.llmkit"  # Default prefix added to all metrics.

    def system_tags(self) -> list[str]:
        """Gather all common tracking tags"""
        return [f"env:{self.env}", f"appname:{self.appname}"]

    def track_count(self, metric: str, tags: list[str]):  # noqa: ANN201, TODO(Huong): Add return value and re-enable this lint.
        tags = tags + self.system_tags()
        return super().track_count(f"{self.prefix}.{metric}", tags)

    def track_count_n(self, metric: str, value: int, tags: list[str]):  # noqa: ANN201, TODO(Huong): Add return value and re-enable this lint.
        tags = tags + self.system_tags()
        return super().track_count_n(f"{self.prefix}.{metric}", value, tags)

    def track_elapsed(self, metric: str, value: int, tags: list[str]):  # noqa: ANN201, TODO(Huong): Add return value and re-enable this lint.
        tags = tags + self.system_tags()
        return super().track_elapsed(f"{self.prefix}.{metric}", value, tags)

    def track_success(self, metric: str, tags: list[str]):  # noqa: ANN201, TODO(Huong): Add return value and re-enable this lint.
        tags = ["success:true"] + tags  # noqa: RUF005, TODO(Huong): Consider `["success:true", *tags]` and re-enable this lint.
        return self.track_count(metric, tags)

    def track_error(self, metric: str, error: str, tags: list[str]):  # noqa: ANN201, TODO(Huong): Add return value and re-enable this lint.
        tags = ["success:false", f"err:{error}"] + tags  # noqa: RUF005, TODO(Huong): Consider `["success:false", f"err:{error}", *tags]` and re-enable this lint.
        return self.track_count(metric, tags)
