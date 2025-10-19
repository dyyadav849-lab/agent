import json
from pathlib import Path

from zion.openapi.http_plugin import (
    HttpPlugin,
    InfoConfig,
    Paramters,
    ServerConfig,
)
from zion.openapi.openapi_plugin import OpenAPIPlugin
from zion.openapi.util import load_openapi_spec_from_http_plugin


def test_load_openapi_spec_from_http_plugin() -> None:
    # Open the JSON file
    # JSON data can get from pluginInfo (UI)
    with Path.open("./zion/openapi/tests/http_plugin_info_model_sample.json") as f:
        # Load the data from the JSON file
        plugin_info = json.load(f)

    plugin_info_model = OpenAPIPlugin(**plugin_info)

    plugin_details = load_openapi_spec_from_http_plugin(
        plugin_info_model.http_plugin_detail
    )

    http_plugin = HttpPlugin(
        openapi=plugin_details["openapi"],
        info=plugin_details["info"],
        servers=plugin_details["servers"],
        components=plugin_details["components"],
        paths=plugin_details["paths"],
    )

    assert isinstance(http_plugin.openapi, str), "openapi must be a string"
    assert isinstance(http_plugin.info, InfoConfig), (
        "info must be an instance of InfoConfig"
    )
    assert isinstance(http_plugin.servers, list), "servers must be a list"
    assert all(isinstance(server, ServerConfig) for server in http_plugin.servers), (
        "all servers must be instances of ServerConfig"
    )
    assert (
        isinstance(http_plugin.components, Paramters) or http_plugin.components is None
    ), "components must be an instance of Paramters or None"
    assert isinstance(http_plugin.paths, dict), "paths must be a dictionary"
    assert all(isinstance(path, str) for path in http_plugin.paths), (
        "all paths must be strings"
    )
