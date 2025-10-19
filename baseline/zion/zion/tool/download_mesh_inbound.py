from typing import Any, Optional

from langchain.tools import BaseTool
from langchain_core.tools import ToolException
from pydantic import BaseModel, Field

from zion.config import logger
from zion.util.convert import correct_env
from zion.util.service_mesh import download_mesh_config


class DownloadMeshInboundToolInput(BaseModel):
    service_name: str = Field(
        description="the service name to get service information."
    )
    env: str = Field(description="the environment.")


class DownloadMeshInboundTool(BaseTool):
    name: str = "download_mesh_inbound"
    description: str = """
    Get service upstream and downstream dependencies.
    """
    args_schema: type[BaseModel] = DownloadMeshInboundToolInput
    handle_tool_error: bool = True
    metadata: Optional[dict[str, Any]] = None

    def _run(self, service_name: str, env: str) -> str:
        """Use the tool."""

        return self.download_mesh_inbound(service_name, env)

    async def _arun(self, service_name: str, env: str) -> str:
        """Use the tool asynchronously."""

        return self.download_mesh_inbound(service_name, env)

    def download_mesh_inbound(self, service_name: str, env: str) -> dict:
        """Get inbound config for given service_name and env. This is used to determine if the service_name is VM or MEKS based on compute_types"""

        try:
            env = correct_env(env)
            if env == "prd_stg":
                prd_mesh_config = download_mesh_config(
                    service_name, "prd", outbound=False
                )
                stg_mesh_config = download_mesh_config(
                    service_name, "stg", outbound=False
                )
                return {"production": prd_mesh_config, "staging": stg_mesh_config}
            return download_mesh_config(service_name, env, outbound=False)

        except Exception as e:
            err_message = f"Unable to download mesh config with exception: {e!s}"
            logger.exception(err_message)
            raise ToolException(err_message) from e
