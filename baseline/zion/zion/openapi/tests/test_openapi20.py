from pathlib import Path
from typing import Any

import yaml

from zion.openapi.openapi20 import reduce_openapi_20_spec
from zion.openapi.util import IncludeOpenAPIPath


def safe_get(dict_obj: dict[str, Any], *keys: str) -> dict[str, Any] | None:
    for key in keys:
        if isinstance(dict_obj, dict):
            dict_obj = dict_obj.get(key)
    return dict_obj


def test_reduce_openapi_20_spec() -> None:
    # read `openapi_20_sample.json` from file
    with Path.open("./zion/openapi/tests/openapi_20_sample.yaml") as f:
        openapi_spec = yaml.safe_load(f)

    reduced_spec = reduce_openapi_20_spec(
        openapi_spec=openapi_spec,
        filter_paths=[
            IncludeOpenAPIPath(path="/hello", method="POST"),
        ],
        ignored_definition_keys=["protobufAny"],
    )

    assert safe_get(reduced_spec, "paths", "/hello", "post") is not None
    assert safe_get(reduced_spec, "paths", "/oidc/callback") is None

    assert (
        safe_get(reduced_spec, "definitions", "tisupportbotpbHelloRequest") is not None
    )
    assert safe_get(reduced_spec, "definitions", "protobufAny") is None
