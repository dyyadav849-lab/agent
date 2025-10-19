import json
import traceback
from typing import Any, Optional, Union

import requests
from langchain.tools import BaseTool
from langchain_core.tools import ToolException
from pydantic import BaseModel, Field

from zion.config import global_config, logger
from zion.util import helix
from zion.util.constant import GRAB_INDEX, K8S_INDEX
from zion.util.convert import correct_env
from zion.util.service_mesh import download_mesh_config

ROLLOUT_PERCENTAGE = 100


class GetServicePlatformInput(BaseModel):
    service_name: str = Field(
        description="the service name to get service information."
    )
    env: str = Field(description="the environment.")


class GetServicePlatformTool(BaseTool):
    name: str = "get_service_platform"
    description: str = """
    Get service platform by gitlab and helix token (k8s OR grab)
    """
    args_schema: type[BaseModel] = GetServicePlatformInput
    handle_tool_error: bool = True
    metadata: Optional[dict[str, Any]] = None

    def _run(self, service_name: str, env: str) -> str:
        """Use the tool."""

        return self.get_service_platform(service_name, env)

    async def _arun(self, service_name: str, env: str) -> str:
        """Use the tool asynchronously."""

        return self.get_service_platform(service_name, env)

    def get_service_platform(self, service_name: str, env: str) -> str:
        """Get service upstream and downstream platform"""
        try:
            env = correct_env(env)
            smi_config = download_mesh_config(service_name, self.convert_env(env))
            if smi_config:
                return self.get_index_from_smi(smi_config, service_name)

            _, helix_token = helix.get_helix_token()()
            if helix_token is None:
                # If helix token is None, return GRAB_INDEX
                return GRAB_INDEX

            service_helix_entity = self.query_service_info(service_name, helix_token)
            if self.is_deployment_repo_present(
                self.get_code_base(service_helix_entity)
            ):
                return K8S_INDEX

            return GRAB_INDEX  # noqa: TRY300
        except (ValueError, KeyError, TypeError) as e:
            traceback.print_exc()
            err_message = f"Unable to get service mesh with exception: {e!s}"
            logger.exception(err_message)
            raise ToolException(err_message) from e

    def convert_env(self, env: str) -> str:
        return "prd" if env in ["dev"] else env

    def get_code_base(
        self,
        app_info: dict[str, Union[str, dict[str, str]]],
    ) -> dict[str, Union[str, bool]]:
        return json.loads(
            app_info.get("metadata", {})
            .get("annotations", {})
            .get("helix.engtools.net/code-base", "{}")
        )

    def is_deployment_repo_present(
        self, code_base_obj: dict[str, Union[str, bool]]
    ) -> bool:
        return code_base_obj.get("deployment", False)

    def query_service_info(self, service: str, token: str) -> dict:
        try:
            response = requests.get(
                f"{global_config.helix_base_url}/api/catalog/entities/by-name/component/default/{service}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5.0,
            )
            if response == "null" or response is None:
                logger.error(
                    f"call helix filter failed when call {service}, plz retry it!"
                )
                return {}
            return response.json()
        except requests.exceptions.RequestException as err:
            logger.error("Oops: Something Else Happened!", err)

    def get_index_from_smi(
        self,
        smi_config: dict[str, Union[str, list[Union[str, dict[str, Union[str, int]]]]]],
        service: str,
    ) -> str:
        return (
            K8S_INDEX
            if "MEKS" in smi_config.get("compute_types", [])
            and any(
                self.is_weight_at_rollout_percentage(item, service)
                for item in smi_config.get(
                    "traffic_split", [{"name": service, "weight": 0}]
                )
            )
            else GRAB_INDEX
        )

    def is_weight_at_rollout_percentage(
        self, item: dict[str, Union[str, int]], service: str
    ) -> bool:
        return item["name"] == service and item["weight"] == ROLLOUT_PERCENTAGE
