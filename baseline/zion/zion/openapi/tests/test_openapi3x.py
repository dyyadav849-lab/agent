from pathlib import Path
from typing import Any

import yaml

from zion.openapi.openapi3x import reduce_openapi_3x_spec
from zion.openapi.util import IncludeOpenAPIPath


def safe_get(dict_obj: dict[str, Any], *keys: str) -> dict[str, Any] | None:
    for key in keys:
        if isinstance(dict_obj, dict):
            dict_obj = dict_obj.get(key)
    return dict_obj


def test_reduce_openapi_3x_spec() -> None:
    with Path.open("./zion/openapi/tests/openapi_3X_sample.yaml") as f:
        openapi_spec = yaml.safe_load(f)

    reduced_spec = reduce_openapi_3x_spec(
        openapi_spec=openapi_spec,
        filter_paths=[
            IncludeOpenAPIPath(path="/health_check", method="GET"),
        ],
        ignored_definition_keys=["HTTPValidationError"],
    )

    assert safe_get(reduced_spec, "paths", "/health_check", "get") is not None
    assert safe_get(reduced_spec, "paths", "/oidc/callback") is None

    assert (
        safe_get(reduced_spec, "components", "schemas", "HealthCheckResponse")
        is not None
    )
    assert (
        safe_get(reduced_spec, "components", "schemas", "HTTPValidationError") is None
    )
