from collections import OrderedDict
from datetime import datetime, timedelta

import pytz
from datadog_api_client import ApiClient, Configuration
from datadog_api_client.exceptions import ApiValueError
from datadog_api_client.v2.api.metrics_api import MetricsApi
from datadog_api_client.v2.model.formula_limit import FormulaLimit
from datadog_api_client.v2.model.metrics_aggregator import MetricsAggregator
from datadog_api_client.v2.model.metrics_data_source import MetricsDataSource
from datadog_api_client.v2.model.metrics_scalar_query import MetricsScalarQuery
from datadog_api_client.v2.model.query_formula import QueryFormula
from datadog_api_client.v2.model.scalar_formula_query_request import (
    ScalarFormulaQueryRequest,
)
from datadog_api_client.v2.model.scalar_formula_request import ScalarFormulaRequest
from datadog_api_client.v2.model.scalar_formula_request_attributes import (
    ScalarFormulaRequestAttributes,
)
from datadog_api_client.v2.model.scalar_formula_request_queries import (
    ScalarFormulaRequestQueries,
)
from datadog_api_client.v2.model.scalar_formula_request_type import (
    ScalarFormulaRequestType,
)

from zion.config import global_config, logger
from zion.util.convert import correct_env

# Constants
DD_EVENT_TYPE = "agent.slack"
DD_TAGS = {
    "stg": "(environment:stg OR env:staging)",
    "prd": "(environment:prod OR env:prd OR env:production)",
}

dd_config = Configuration(
    server_variables={
        "site": global_config.datadog_site,
    },
    api_key={
        "apiKeyAuth": global_config.datadog_api_key,
        "appKeyAuth": global_config.datadog_app_key,
    },
)


# async def get_downstream_qps(service_name: str) -> dict:
def get_downstream_qps(service_name: str, env: str, endpoint_name: str = "*") -> dict:
    env = correct_env(env)
    if env == "":
        return {"Error": f"Environment value `{env}` is missing or not supported."}

    dd_config.unstable_operations["query_scalar_data"] = True
    api_client = ApiClient(dd_config)
    default_tags = DD_TAGS[env]
    body = ScalarFormulaQueryRequest(
        data=ScalarFormulaRequest(
            attributes=ScalarFormulaRequestAttributes(
                formulas=[
                    QueryFormula(
                        formula="query1",
                        limit=FormulaLimit(50),
                    ),
                ],
                queries=ScalarFormulaRequestQueries(
                    [
                        MetricsScalarQuery(
                            aggregator=MetricsAggregator.AVG,
                            data_source=MetricsDataSource.METRICS,
                            query=f"sum:gostatsd.grabkit.middleware.stats.elapsed.count{{{default_tags} AND type:server AND appname:{service_name} AND endpoint:{endpoint_name} }} by {{client}}.as_rate()",
                            name="query1",
                        ),
                    ]
                ),
                _from=int(
                    (
                        datetime.now(tz=pytz.timezone("Asia/Singapore"))
                        - timedelta(days=7)
                    ).timestamp()
                    * 1000
                ),
                to=int(
                    datetime.now(tz=pytz.timezone("Asia/Singapore")).timestamp() * 1000
                ),
            ),
            type=ScalarFormulaRequestType.SCALAR_REQUEST,
        ),
    )
    api_instance = MetricsApi(api_client)
    try:
        response = api_instance.query_scalar_data(body=body)
        logger.info(f"DEBUG: get_downstream_qps got Response: {response}")
        if (
            response.data
            and response.data.attributes
            and response.data.attributes.columns
        ):
            columns = response.data.attributes.columns
            service_column = next(
                (col for col in columns if col.name == "client"), None
            )
            query1_column = next((col for col in columns if col.name == "query1"), None)

            if service_column and query1_column:
                service_values = service_column.values
                query1_values = query1_column.values

                result = OrderedDict()
                for i in range(len(service_values)):
                    service = service_values[i][0].split(".")[0]
                    value = query1_values[i]
                    if service not in ["N/A", "unknown"]:
                        result[service] = value

                return dict(sorted(result.items(), key=lambda x: x[1], reverse=True))
        else:
            return {}
    except ApiValueError as e:
        logger.warn(
            f"get_downstream_qps for service name `{service_name}` in `{env}` got exception: {e}",
            tags={"event_type": DD_EVENT_TYPE},
        )
        return {}


def get_upstream_qps(service_name: str, env: str) -> dict:
    env = correct_env(env)
    if env == "":
        return {"Error": f"Environment value `{env}` is missing or not supported."}

    dd_config.unstable_operations["query_scalar_data"] = True
    api_client = ApiClient(dd_config)
    default_tags = DD_TAGS[env]
    body = ScalarFormulaQueryRequest(
        data=ScalarFormulaRequest(
            attributes=ScalarFormulaRequestAttributes(
                formulas=[
                    QueryFormula(
                        formula="query1",
                        limit=FormulaLimit(50),
                    ),
                ],
                queries=ScalarFormulaRequestQueries(
                    [
                        MetricsScalarQuery(
                            aggregator=MetricsAggregator.AVG,
                            data_source=MetricsDataSource.METRICS,
                            query=f"sum:gostatsd.grabkit.middleware.stats.elapsed.count{{{default_tags} AND type:server AND client:{service_name}}} by {{appname}}.as_rate()",
                            name="query1",
                        ),
                    ]
                ),
                _from=int(
                    (
                        datetime.now(tz=pytz.timezone("Asia/Singapore"))
                        - timedelta(days=7)
                    ).timestamp()
                    * 1000
                ),
                to=int(
                    datetime.now(tz=pytz.timezone("Asia/Singapore")).timestamp() * 1000
                ),
            ),
            type=ScalarFormulaRequestType.SCALAR_REQUEST,
        ),
    )
    api_instance = MetricsApi(api_client)
    try:
        response = api_instance.query_scalar_data(body=body)
        logger.info(
            f"DEBUG: get_upstream_qps got Response: {response}",
            tags={"event_type": DD_EVENT_TYPE},
        )
        if (
            response.data
            and response.data.attributes
            and response.data.attributes.columns
        ):
            columns = response.data.attributes.columns
            service_column = next(
                (col for col in columns if col.name == "appname"), None
            )
            query1_column = next((col for col in columns if col.name == "query1"), None)

            if service_column and query1_column:
                service_values = service_column.values
                query1_values = query1_column.values

                result = OrderedDict()
                for i in range(len(service_values)):
                    service = service_values[i][0].split(".")[0]
                    value = query1_values[i]
                    if service not in ["N/A", "unknown"]:
                        result[service] = value

                return dict(sorted(result.items(), key=lambda x: x[1], reverse=True))
        else:
            return {}
    except ApiValueError as e:
        logger.warn(
            f"get_upstream_qps for service name `{service_name}` in `{env}` got exception: {e}",
            tags={"event_type": DD_EVENT_TYPE},
        )
        return {}
